from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from extensions import db
from models import Formation, Module, Enseignant, Affectation, Seance

views_bp = Blueprint('views', __name__)


def get_current_formation():
    """Formation sélectionnée en session (côté consultation)."""
    fid = session.get('view_formation_id')
    if fid:
        f = Formation.query.get(fid)
        if f:
            return f
    f = Formation.query.first()
    if f:
        session['view_formation_id'] = f.id
    return f


@views_bp.route('/set-formation', methods=['POST'])
def set_formation():
    fid = request.form.get('formation_id', type=int)
    if fid and Formation.query.get(fid):
        session['view_formation_id'] = fid
    next_url = request.form.get('next') or url_for('views.index')
    return redirect(next_url)


@views_bp.route('/')
def index():
    formation  = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    return render_template('views/index.html', formation=formation, formations=formations)

# ─────────────────────────────────────────────
# CONNEXION (SIMULATION)
# ─────────────────────────────────────────────

@views_bp.route('/login-etudiant', methods=['GET', 'POST'])
def login_etudiant():
    if request.method == 'POST':
        session['role'] = 'etudiant'
        return redirect(url_for('views.etudiant'))
    # Si déjà connecté
    if session.get('role') == 'etudiant':
        return redirect(url_for('views.etudiant'))
    return render_template('views/login_etudiant.html')

@views_bp.route('/login-enseignant', methods=['GET', 'POST'])
def login_enseignant():
    if request.method == 'POST':
        email = request.form.get('identifiant')
        password = request.form.get('password')
        
        # On va chercher par email
        ens = Enseignant.query.filter(Enseignant.email == email).first()
        if not ens:
            # Fallback par nom complet (si l'utilisateur tape juste "Nom")
            ens = Enseignant.query.filter(Enseignant.nom.ilike(f'%{email}%')).first()

        if ens and ens.password == password:
            session['role'] = 'enseignant'
            session['enseignant_id'] = ens.id
            return redirect(url_for('views.enseignant'))
        else:
            flash("Identifiant ou mot de passe incorrect.", "danger")
            
    # Si déjà connecté
    if session.get('role') == 'enseignant' and session.get('enseignant_id'):
        return redirect(url_for('views.enseignant'))
    return render_template('views/login_enseignant.html')

@views_bp.route('/logout')
def logout():
    session.pop('role', None)
    session.pop('enseignant_id', None)
    return redirect(url_for('portal'))

# ─────────────────────────────────────────────
# VUE ÉTUDIANT
# ─────────────────────────────────────────────

@views_bp.route('/etudiant')
def etudiant():
    formation  = get_current_formation()
    formations = Formation.query.order_by(Formation.nom).all()
    vue = request.args.get('vue', '')          # '' | 'promo' | 'TD1' | 'TD2'...
    seances = []
    events_url = ''

    if vue and formation:
        if vue == 'promo':
            # Toutes les séances de la formation
            seances = (Seance.query.join(Module)
                       .filter(Module.formation_id == formation.id)
                       .order_by(Seance.date, Seance.heure_debut).all())
            events_url = url_for('views.api_events')
        elif vue.startswith('Groupe'):
            # CM (Promo) + le groupe
            groupes = ['Promo', vue]
            seances = (Seance.query.join(Module)
                       .filter(Module.formation_id == formation.id,
                               Seance.groupe.in_(groupes))
                       .order_by(Seance.date, Seance.heure_debut).all())
            events_url = url_for('views.api_events') + f'?vue_td={vue}'

    return render_template('views/etudiant.html',
                           formation=formation, formations=formations,
                           current_vue=vue, seances=seances, events_url=events_url)


# ─────────────────────────────────────────────
# VUE ENSEIGNANT
# ─────────────────────────────────────────────

@views_bp.route('/enseignant')
def enseignant():
    formations = Formation.query.order_by(Formation.nom).all()
    enseignant_id      = session.get('enseignant_id')
    formation_filter   = request.args.get('formation_filter', 'all')  # 'all' or formation id
    enseignant_obj = None
    seances = []
    affectations = []
    events_url = ''
    selected_formation_id = formation_filter

    if not enseignant_id:
        return redirect(url_for('views.login_enseignant'))

    enseignant_obj = Enseignant.query.get(enseignant_id)
    if enseignant_obj:
        q = Seance.query.join(Module).filter(Seance.enseignant_id == enseignant_id)

        # Filtrer par formation si nécessaire
        if formation_filter != 'all':
            try:
                fid = int(formation_filter)
                q = q.filter(Module.formation_id == fid)
            except (ValueError, TypeError):
                pass

        seances = q.order_by(Seance.date, Seance.heure_debut).all()
        affectations = Affectation.query.join(Module).filter(
            Affectation.enseignant_id == enseignant_id
        ).all()

        params = f'enseignant_id={enseignant_id}'
        if formation_filter != 'all':
            params += f'&formation_filter={formation_filter}'
        events_url = url_for('views.api_events') + '?' + params

    return render_template('views/enseignant.html',
                           formations=formations,
                           enseignant=enseignant_obj, seances=seances,
                           affectations=affectations,
                           events_url=events_url,
                           selected_formation_id=selected_formation_id)


# ─────────────────────────────────────────────
# API JSON FullCalendar
# ─────────────────────────────────────────────

@views_bp.route('/api/events')
def api_events():
    formation     = get_current_formation()
    enseignant_id = request.args.get('enseignant_id', '', type=int)
    formation_filter = request.args.get('formation_filter', '')
    q = Seance.query.join(Module)

    if enseignant_id:
        # Vue enseignant = ses cours uniquement
        q = q.filter(Seance.enseignant_id == enseignant_id)
        if formation_filter and formation_filter != 'all':
            try:
                q = q.filter(Module.formation_id == int(formation_filter))
            except (ValueError, TypeError):
                pass
    else:
        # Vue globale / vue étudiant = filtre par formation courante
        if formation:
            q = q.filter(Module.formation_id == formation.id)

    # Mode vue par groupe
    vue_td = request.args.get('vue_td', '')
    if vue_td and formation:
        q = q.filter(Seance.groupe.in_(['Promo', vue_td]))
    else:
        groupe = request.args.get('groupe', '')
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
            'title': f"[{s.type_seance}] {s.module.code}",
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
                'formation':      s.module.formation.nom,
                'salle':          s.salle or '',
            }
        })
    return jsonify(events)
