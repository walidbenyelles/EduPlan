from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from extensions import db
from models import Formation, Module, Enseignant, Affectation, Seance
from forms import FormationForm, ModuleForm, EnseignantForm, AffectationForm, SeanceForm
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_current_formation():
    """Retourne la formation sélectionnée en session, sinon la première."""
    fid = session.get('formation_id')
    if fid:
        f = Formation.query.get(fid)
        if f:
            return f
    f = Formation.query.first()
    if f:
        session['formation_id'] = f.id
    return f


def check_quota(module_id, type_seance, groupe, duree_minutes, exclude_id=None):
    """Retourne (ok, message). Vérifie que le quota maquette n'est pas dépassé."""
    module = Module.query.get(module_id)
    if not module:
        return False, "Module introuvable."

    quota_h = {'CM': module.h_cm_prevues, 'TD': module.h_td_prevues, 'TP': module.h_tp_prevues}.get(type_seance, 0)
    if quota_h == 0:
        return True, None

    q = db.session.query(func.sum(Seance.duree_minutes)).filter_by(
        module_id=module_id, type_seance=type_seance
    )
    if type_seance in ('TD', 'TP'):
        q = q.filter(Seance.groupe == groupe)
    if exclude_id:
        q = q.filter(Seance.id != exclude_id)

    deja_min = q.scalar() or 0
    total_min = deja_min + duree_minutes
    quota_min = quota_h * 60

    if total_min > quota_min:
        deja_h = round(deja_min / 60, 1)
        total_h = round(total_min / 60, 1)
        return False, (f"⚠️ Dépassement de quota {type_seance} pour « {module.libelle} » "
                       f"(groupe {groupe}) : {deja_h}h déjà planifiées + {round(duree_minutes/60,1)}h "
                       f"= {total_h}h > {quota_h}h prévues.")
    return True, None


def heure_to_min(h):
    hh, mm = map(int, h.split(':'))
    return hh * 60 + mm


def check_conflict(groupe, jour, heure_debut, duree_minutes, formation, exclude_id=None):
    """Vérifie qu'aucun groupe lié n'a déjà une séance qui chevauche ce créneau.
    Retourne (ok, message).
    """
    if not formation:
        return True, None

    # Déterminer les groupes qui partagent des étudiants avec 'groupe'
    # Nouveau modèle : Promo contient tout le monde.
    # Un groupe spécifique "Groupe X" ne chevauche que lui-même et la Promo.
    if groupe == 'Promo':
        groupes_lies = ['Promo'] + formation.groupes
    else:
        groupes_lies = ['Promo', groupe]

    # Récupérer toutes les séances de ces groupes ce jour-là (filtrées sur la formation)
    s_debut = heure_to_min(heure_debut)
    s_fin   = s_debut + duree_minutes

    existantes = (Seance.query.join(Module)
                  .filter(Module.formation_id == formation.id,
                          Seance.date == jour,
                          Seance.groupe.in_(groupes_lies)))
    if exclude_id:
        existantes = existantes.filter(Seance.id != exclude_id)

    for s in existantes.all():
        e_debut = heure_to_min(s.heure_debut)
        e_fin   = e_debut + s.duree_minutes
        if s_debut < e_fin and e_debut < s_fin:
            return False, (
                f"⛔ Conflit de planning : le groupe « {s.groupe} » a déjà "
                f"[{s.type_seance}] {s.module.code} de {s.heure_debut} à {s.heure_fin} "
                f"le {jour.strftime('%d/%m/%Y')}."
            )
    return True, None


def check_teacher_conflict(enseignant_id, jour, heure_debut, duree_minutes, exclude_id=None):
    """Vérifie qu'un enseignant n'a pas déjà cours à ce moment-là."""
    s_debut = heure_to_min(heure_debut)
    s_fin   = s_debut + duree_minutes

    existantes = Seance.query.filter(
        Seance.enseignant_id == enseignant_id,
        Seance.date == jour
    )
    if exclude_id:
        existantes = existantes.filter(Seance.id != exclude_id)

    for s in existantes.all():
        e_debut = heure_to_min(s.heure_debut)
        e_fin   = e_debut + s.duree_minutes
        if s_debut < e_fin and e_debut < s_fin:
            return False, (
                f"⛔ Conflit Enseignant : {s.enseignant.nom_complet} donne déjà le cours "
                f"[{s.type_seance}] {s.module.code} de {s.heure_debut} à {s.heure_fin}."
            )
    return True, None


def get_groupe_choices(formation):
    if not formation:
        return [('Promo', 'Promo')]
    return [(g, g) for g in formation.all_groupes]


# ─────────────────────────────────────────────
# CHANGER DE FORMATION (session)
# ─────────────────────────────────────────────

@admin_bp.route('/set-formation', methods=['POST'])
def set_formation():
    fid = request.form.get('formation_id', type=int)
    if fid and Formation.query.get(fid):
        session['formation_id'] = fid
    next_url = request.form.get('next') or url_for('admin.dashboard')
    return redirect(next_url)


# ─────────────────────────────────────────────
# CONNEXION (SIMULATION)
# ─────────────────────────────────────────────

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/login_admin.html')


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@admin_bp.route('/')
def dashboard():
    formation   = get_current_formation()
    formations  = Formation.query.order_by(Formation.nom).all()
    modules     = Module.query.filter_by(formation_id=formation.id).all() if formation else []
    alertes     = [m for m in modules if m.has_alert()]
    nb_seances  = Seance.query.join(Module).filter(
        Module.formation_id == formation.id).count() if formation else 0
    nb_enseignants = Enseignant.query.count()

    def total_h(type_s):
        if not formation:
            return 0
        res = db.session.query(func.sum(Seance.duree_minutes))\
            .join(Module).filter(Module.formation_id == formation.id,
                                 Seance.type_seance == type_s).scalar()
        return round((res or 0) / 60, 1)

    def total_prevues(type_s):
        if not formation:
            return 0
        field = {'CM': Module.h_cm_prevues, 'TD': Module.h_td_prevues, 'TP': Module.h_tp_prevues}[type_s]
        res = db.session.query(func.sum(field)).filter(Module.formation_id == formation.id).scalar()
        return round(res or 0, 1)

    stats = {t: {'planifiees': total_h(t), 'prevues': total_prevues(t)} for t in ['CM', 'TD', 'TP']}
    return render_template('admin/dashboard.html',
                           formation=formation, formations=formations,
                           modules=modules, alertes=alertes,
                           nb_seances=nb_seances, nb_enseignants=nb_enseignants, stats=stats)


# ─────────────────────────────────────────────
# FORMATION (CRUD)
# ─────────────────────────────────────────────

@admin_bp.route('/formation', methods=['GET', 'POST'])
def formation():
    formations = Formation.query.order_by(Formation.nom).all()
    obj = get_current_formation()
    form = FormationForm(obj=obj)
    if form.validate_on_submit():
        if obj:
            obj.nom = form.nom.data
            obj.nb_groupes = form.nb_groupes.data
        else:
            obj = Formation(nom=form.nom.data,
                            nb_groupes=form.nb_groupes.data)
            db.session.add(obj)
            db.session.flush()
            session['formation_id'] = obj.id
        db.session.commit()
        flash('Formation enregistrée avec succès.', 'success')
        return redirect(url_for('admin.formation'))
    return render_template('admin/formation.html', form=form, formation=obj, formations=formations)


@admin_bp.route('/formation/new', methods=['GET', 'POST'])
def formation_new():
    form = FormationForm()
    if form.validate_on_submit():
        obj = Formation(nom=form.nom.data,
                        nb_groupes=form.nb_groupes.data)
        db.session.add(obj)
        db.session.flush()
        session['formation_id'] = obj.id
        db.session.commit()
        flash(f'Formation « {obj.nom} » créée et sélectionnée.', 'success')
        return redirect(url_for('admin.formation'))
    return render_template('admin/formation_new.html', form=form)


@admin_bp.route('/formation/<int:fid>/delete', methods=['POST'])
def formation_delete(fid):
    obj = Formation.query.get_or_404(fid)
    db.session.delete(obj)
    db.session.commit()
    if session.get('formation_id') == fid:
        session.pop('formation_id', None)
    flash(f'Formation « {obj.nom} » supprimée.', 'info')
    return redirect(url_for('admin.formation'))


# ─────────────────────────────────────────────
# MODULES
# ─────────────────────────────────────────────

@admin_bp.route('/modules', methods=['GET', 'POST'])
def modules():
    formation = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    if not formation:
        flash('Veuillez d\'abord créer une formation.', 'warning')
        return redirect(url_for('admin.formation'))
    form = ModuleForm()
    if form.validate_on_submit():
        m = Module(code=form.code.data, libelle=form.libelle.data,
                   h_cm_prevues=form.h_cm_prevues.data or 0,
                   h_td_prevues=form.h_td_prevues.data or 0,
                   h_tp_prevues=form.h_tp_prevues.data or 0,
                   formation_id=formation.id)
        db.session.add(m)
        db.session.commit()
        flash(f'Module « {m.code} » ajouté.', 'success')
        return redirect(url_for('admin.modules'))
    liste = Module.query.filter_by(formation_id=formation.id).order_by(Module.id.desc()).all()
    return render_template('admin/modules.html', form=form, modules=liste,
                           formation=formation, formations=formations)


@admin_bp.route('/modules/<int:mid>/edit', methods=['GET', 'POST'])
def module_edit(mid):
    m = Module.query.get_or_404(mid)
    form = ModuleForm(obj=m)
    if form.validate_on_submit():
        m.code = form.code.data
        m.libelle = form.libelle.data
        m.h_cm_prevues = form.h_cm_prevues.data or 0
        m.h_td_prevues = form.h_td_prevues.data or 0
        m.h_tp_prevues = form.h_tp_prevues.data or 0
        db.session.commit()
        flash(f'Module « {m.code} » mis à jour.', 'success')
        return redirect(url_for('admin.modules'))
    return render_template('admin/module_edit.html', form=form, module=m)


@admin_bp.route('/modules/<int:mid>/delete', methods=['POST'])
def module_delete(mid):
    m = Module.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    flash(f'Module « {m.code} » supprimé.', 'info')
    return redirect(url_for('admin.modules'))


# ─────────────────────────────────────────────
# ENSEIGNANTS
# ─────────────────────────────────────────────

@admin_bp.route('/enseignants', methods=['GET', 'POST'])
def enseignants():
    formation  = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    if not formation:
        flash('Veuillez d\'abord créer une formation.', 'warning')
        return redirect(url_for('admin.formation'))
        
    form = EnseignantForm()
    if form.validate_on_submit():
        e = Enseignant(nom=form.nom.data, prenom=form.prenom.data, email=form.email.data, password='password123')
        db.session.add(e)
        db.session.commit()
        flash(f'{e.nom_complet} ajouté.', 'success')
        return redirect(url_for('admin.enseignants'))
    liste = Enseignant.query.order_by(Enseignant.nom).all()
    return render_template('admin/enseignants.html', form=form, enseignants=liste,
                           formation=formation, formations=formations)


@admin_bp.route('/enseignants/<int:eid>/delete', methods=['POST'])
def enseignant_delete(eid):
    e = Enseignant.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    flash('Enseignant supprimé.', 'info')
    return redirect(url_for('admin.enseignants'))


# ─────────────────────────────────────────────
# AFFECTATIONS
# ─────────────────────────────────────────────

@admin_bp.route('/affectations', methods=['GET', 'POST'])
def affectations():
    formation  = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    form = AffectationForm()
    form.enseignant_id.choices = [(e.id, e.nom_complet) for e in Enseignant.query.order_by(Enseignant.nom).all()]
    # Modules filtrés sur la formation courante
    mods = Module.query.filter_by(formation_id=formation.id).all() if formation else []
    form.module_id.choices = [(m.id, f"{m.code} — {m.libelle}") for m in mods]

    if form.validate_on_submit():
        existing = Affectation.query.filter_by(
            enseignant_id=form.enseignant_id.data,
            module_id=form.module_id.data
        ).first()
        if existing:
            existing.h_cm_attribuees = form.h_cm_attribuees.data or 0
            existing.h_td_attribuees = form.h_td_attribuees.data or 0
            existing.h_tp_attribuees = form.h_tp_attribuees.data or 0
            flash('Affectation mise à jour.', 'success')
        else:
            aff = Affectation(
                enseignant_id=form.enseignant_id.data,
                module_id=form.module_id.data,
                h_cm_attribuees=form.h_cm_attribuees.data or 0,
                h_td_attribuees=form.h_td_attribuees.data or 0,
                h_tp_attribuees=form.h_tp_attribuees.data or 0
            )
            db.session.add(aff)
            flash('Affectation créée.', 'success')
        db.session.commit()
        return redirect(url_for('admin.affectations'))

    # Liste des affectations filtrées sur la formation courante
    liste = (Affectation.query.join(Module)
             .filter(Module.formation_id == formation.id)
             .order_by(Affectation.id.desc()).all()) if formation else []
    return render_template('admin/affectations.html', form=form, affectations=liste,
                           formation=formation, formations=formations)


@admin_bp.route('/affectations/<int:aid>/delete', methods=['POST'])
def affectation_delete(aid):
    a = Affectation.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    flash('Affectation supprimée.', 'info')
    return redirect(url_for('admin.affectations'))


# ─────────────────────────────────────────────
# SÉANCES (Ajout + Liste)
# ─────────────────────────────────────────────

@admin_bp.route('/seances', methods=['GET', 'POST'])
def seances():
    formation  = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    form = SeanceForm()
    mods = Module.query.filter_by(formation_id=formation.id).all() if formation else []
    form.module_id.choices = [(m.id, f"{m.code} — {m.libelle}") for m in mods]
    form.enseignant_id.choices = [(e.id, e.nom_complet) for e in Enseignant.query.order_by(Enseignant.nom).all()]
    form.groupe.choices = get_groupe_choices(formation)

    if form.validate_on_submit():
        ok, msg = check_quota(form.module_id.data, form.type_seance.data,
                              form.groupe.data, form.duree_minutes.data)
        if not ok:
            flash(msg, 'danger')
        else:
            ok2, msg2 = check_conflict(
                form.groupe.data, form.date.data,
                form.heure_debut.data, form.duree_minutes.data,
                formation
            )
            if not ok2:
                flash(msg2, 'danger')
            else:
                ok3, msg3 = check_teacher_conflict(
                    form.enseignant_id.data, form.date.data,
                    form.heure_debut.data, form.duree_minutes.data
                )
                if not ok3:
                    flash(msg3, 'danger')
                else:
                    s = Seance(
                        module_id=form.module_id.data,
                        enseignant_id=form.enseignant_id.data,
                        type_seance=form.type_seance.data,
                        groupe=form.groupe.data,
                        date=form.date.data,
                        heure_debut=form.heure_debut.data,
                        duree_minutes=form.duree_minutes.data,
                        salle=form.salle.data or None
                    )
                    db.session.add(s)
                    db.session.commit()
                    flash('Séance planifiée avec succès.', 'success')
                    return redirect(url_for('admin.seances'))

    filtre_groupe = request.args.get('groupe', '')
    filtre_module = request.args.get('module_id', '', type=str)
    q = Seance.query.join(Module).join(Enseignant)
    if formation:
        q = q.filter(Module.formation_id == formation.id)
    if filtre_groupe:
        q = q.filter(Seance.groupe == filtre_groupe)
    if filtre_module:
        q = q.filter(Seance.module_id == int(filtre_module))
    seances_list = q.order_by(Seance.id.desc()).all()

    return render_template('admin/seances.html', form=form, seances=seances_list,
                           formation=formation, formations=formations,
                           filtre_groupe=filtre_groupe, filtre_module=filtre_module,
                           modules_liste=mods)


@admin_bp.route('/seances/<int:sid>/delete', methods=['POST'])
def seance_delete(sid):
    s = Seance.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash('Séance supprimée.', 'info')
    return redirect(url_for('admin.seances'))

@admin_bp.route('/api/affected_teachers/<int:module_id>')
def api_affected_teachers(module_id):
    affectations = Affectation.query.filter_by(module_id=module_id).all()
    teachers = [{'id': a.enseignant.id, 'name': a.enseignant.nom_complet} for a in affectations]
    return jsonify(teachers)

# ─────────────────────────────────────────────
# PLANNING (Emploi du temps — Calendrier)
# ─────────────────────────────────────────────

@admin_bp.route('/planning')
def planning():
    formation  = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    mods       = Module.query.filter_by(formation_id=formation.id).all() if formation else []
    filtre_groupe = request.args.get('groupe', '')
    filtre_module = request.args.get('module_id', '', type=str)
    return render_template('admin/planning.html',
                           formation=formation, formations=formations,
                           modules_liste=mods,
                           filtre_groupe=filtre_groupe,
                           filtre_module=filtre_module)


@admin_bp.route('/api/events')
def api_events():
    formation = get_current_formation()
    q = Seance.query.join(Module)
    if formation:
        q = q.filter(Module.formation_id == formation.id)

    # Mode vue par groupe
    vue_groupe = request.args.get('vue_td', '') # On garde ce paramètre pour la compatibilité (mais il s'appelle 'vue_td' dans le js fullcalendar)
    if vue_groupe and formation:
        q = q.filter(Seance.groupe.in_(['Promo', vue_groupe]))
    else:
        # Filtres classiques indépendants
        groupe    = request.args.get('groupe', '')
        if groupe:
            q = q.filter(Seance.groupe == groupe)
            
    module_id = request.args.get('module_id', '', type=int)
    if module_id:
        q = q.filter(Seance.module_id == module_id)

    seances = q.all()
    colors = {'CM': '#4f46e5', 'TD': '#0891b2', 'TP': '#059669'}
    events = []
    for s in seances:
        color = colors.get(s.type_seance, '#6b7280')
        events.append({
            'id': s.id,
            'title': f"[{s.type_seance}] {s.module.code} · {s.groupe}",
            'start': f"{s.date}T{s.heure_debut}",
            'end':   f"{s.date}T{s.heure_fin}",
            'backgroundColor': color,
            'borderColor':     color,
            'textColor': '#ffffff',
            'extendedProps': {
                'type_seance':    s.type_seance,
                'module':         s.module.libelle,
                'module_code':    s.module.code,
                'groupe':         s.groupe,
                'enseignant':     s.enseignant.nom_complet,
                'enseignant_nom': s.enseignant.nom_complet,
                'salle':          s.salle or '',
            }
        })
    return jsonify(events)
