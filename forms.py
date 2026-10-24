from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, HiddenField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Optional, NumberRange, Email


class FormationForm(FlaskForm):
    nom = StringField('Nom de la formation', validators=[DataRequired()])
    nb_groupes = IntegerField('Nombre de groupes (Classes)', validators=[DataRequired(), NumberRange(min=1, max=20)])


class ModuleForm(FlaskForm):
    code = StringField('Code UE', validators=[DataRequired()])
    libelle = StringField('Libellé', validators=[DataRequired()])
    h_cm_prevues = FloatField('Heures CM prévues', validators=[Optional(), NumberRange(min=0)])
    h_td_prevues = FloatField('Heures TD prévues', validators=[Optional(), NumberRange(min=0)])
    h_tp_prevues = FloatField('Heures TP prévues', validators=[Optional(), NumberRange(min=0)])


class EnseignantForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired()])
    prenom = StringField('Prénom', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])


class AffectationForm(FlaskForm):
    enseignant_id = SelectField('Enseignant', coerce=int, validators=[DataRequired()])
    module_id = SelectField('Module', coerce=int, validators=[DataRequired()])
    h_cm_attribuees = FloatField('H. CM attribuées', validators=[Optional(), NumberRange(min=0)], default=0)
    h_td_attribuees = FloatField('H. TD attribuées', validators=[Optional(), NumberRange(min=0)], default=0)
    h_tp_attribuees = FloatField('H. TP attribuées', validators=[Optional(), NumberRange(min=0)], default=0)


class SeanceForm(FlaskForm):
    module_id = SelectField('Module', coerce=int, validators=[DataRequired()])
    enseignant_id = SelectField('Enseignant', coerce=int, validators=[DataRequired()])
    type_seance = SelectField('Type', choices=[('CM', 'CM — Cours Magistral'), ('TD', 'TD — Travaux Dirigés'), ('TP', 'TP — Travaux Pratiques')], validators=[DataRequired()])
    groupe = SelectField('Groupe', choices=[], validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    heure_debut = StringField('Heure de début (HH:MM)', validators=[DataRequired()])
    duree_minutes = IntegerField('Durée (minutes)', validators=[DataRequired(), NumberRange(min=15, max=480)])
    salle = StringField('Salle', validators=[Optional()])
