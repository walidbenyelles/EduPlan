from extensions import db
from sqlalchemy import func


class Formation(db.Model):
    __tablename__ = 'formation'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    nb_groupes = db.Column(db.Integer, default=2)

    modules = db.relationship('Module', backref='formation', lazy=True, cascade='all, delete-orphan')

    @property
    def groupes(self):
        return [f'Groupe {i+1}' for i in range(self.nb_groupes)]

    @property
    def all_groupes(self):
        return ['Promo'] + self.groupes


class Module(db.Model):
    __tablename__ = 'module'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    libelle = db.Column(db.String(200), nullable=False)
    h_cm_prevues = db.Column(db.Float, default=0)
    h_td_prevues = db.Column(db.Float, default=0)
    h_tp_prevues = db.Column(db.Float, default=0)
    formation_id = db.Column(db.Integer, db.ForeignKey('formation.id'), nullable=False)

    seances = db.relationship('Seance', backref='module', lazy=True, cascade='all, delete-orphan')
    affectations = db.relationship('Affectation', backref='module', lazy=True, cascade='all, delete-orphan')

    def heures_planifiees(self, type_seance, groupe=None):
        q = db.session.query(func.sum(Seance.duree_minutes)).filter_by(
            module_id=self.id, type_seance=type_seance
        )
        if groupe:
            q = q.filter(Seance.groupe == groupe)
        return (q.scalar() or 0) / 60

    def pct_type(self, type_seance):
        prevues = {'CM': self.h_cm_prevues, 'TD': self.h_td_prevues, 'TP': self.h_tp_prevues}.get(type_seance, 0)
        if prevues == 0:
            return 0
        return min(100, round(self.heures_planifiees(type_seance) / prevues * 100))

    def statut_type(self, type_seance):
        pct = self.pct_type(type_seance)
        if pct >= 100:
            return 'danger'
        elif pct >= 75:
            return 'warning'
        return 'success'

    def has_alert(self):
        for t in ['CM', 'TD', 'TP']:
            prevues = {'CM': self.h_cm_prevues, 'TD': self.h_td_prevues, 'TP': self.h_tp_prevues}[t]
            if prevues > 0 and self.heures_planifiees(t) > prevues:
                return True
        return False


class Enseignant(db.Model):
    __tablename__ = 'enseignant'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    password = db.Column(db.String(200), nullable=True)
    formation_id = db.Column(db.Integer, db.ForeignKey('formation.id'), nullable=True)

    seances = db.relationship('Seance', backref='enseignant', lazy=True)
    affectations = db.relationship('Affectation', backref='enseignant', lazy=True, cascade='all, delete-orphan')

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


class Affectation(db.Model):
    __tablename__ = 'affectation'
    id = db.Column(db.Integer, primary_key=True)
    enseignant_id = db.Column(db.Integer, db.ForeignKey('enseignant.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    h_cm_attribuees = db.Column(db.Float, default=0)
    h_td_attribuees = db.Column(db.Float, default=0)
    h_tp_attribuees = db.Column(db.Float, default=0)

    def heures_effectuees(self, type_seance):
        result = db.session.query(func.sum(Seance.duree_minutes)).filter_by(
            module_id=self.module_id,
            enseignant_id=self.enseignant_id,
            type_seance=type_seance
        ).scalar()
        return (result or 0) / 60

    def pct_service(self, type_seance):
        attribuees = {'CM': self.h_cm_attribuees, 'TD': self.h_td_attribuees, 'TP': self.h_tp_attribuees}.get(type_seance, 0)
        if attribuees == 0:
            return 0
        return min(100, round(self.heures_effectuees(type_seance) / attribuees * 100))


class Seance(db.Model):
    __tablename__ = 'seance'
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    enseignant_id = db.Column(db.Integer, db.ForeignKey('enseignant.id'), nullable=False)
    type_seance = db.Column(db.String(5), nullable=False)
    groupe = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.String(5), nullable=False)
    duree_minutes = db.Column(db.Integer, nullable=False)
    salle = db.Column(db.String(50), nullable=True)

    @property
    def heure_fin(self):
        h, m = map(int, self.heure_debut.split(':'))
        total = h * 60 + m + self.duree_minutes
        return f"{total // 60:02d}:{total % 60:02d}"

    @property
    def duree_heures(self):
        return self.duree_minutes / 60
