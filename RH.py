import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import zipfile
import os
import shutil
from PIL import Image

st.set_page_config(page_title="Application Web RH – OMNIS", layout="wide")

st.title("📋 Gestion RH OMNIS")

# Initialisation de session_state pour suivre les uploads
if 'files_loaded' not in st.session_state:
    st.session_state.files_loaded = False
if 'data' not in st.session_state:
    st.session_state.data = None
if 'total_employes' not in st.session_state:
    st.session_state.total_employes = 0

# Fonction pour formater les montants en Ariary avec espace comme séparateur
def format_ar(value):
    if pd.isna(value):
        return "N/A"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return str(value)
    formatted = f"{value:,.2f}".replace(",", " ")
    return f"{formatted} Ar"

# Fonction pour formater les colonnes monétaires d'un DataFrame
def format_monetary_columns(df):
    if df.empty:
        return df
    df_formatted = df.copy()
    monetary_keywords = ["salaire", "bonus", "montant", "prime", "indemnité", "sanction", "coût", "cout", "depense", "dépense"]
    for col in df_formatted.columns:
        if any(keyword in col.lower() for keyword in monetary_keywords):
            df_formatted[col] = pd.to_numeric(df_formatted[col], errors='coerce')
            df_formatted[col] = df_formatted[col].apply(format_ar)
    return df_formatted

# Fonction pour formater une date en français (ex. : 22 janvier 2025)
def format_french_date(value):
    if pd.isna(value):
        return "N/A"
    months = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril',
        5: 'mai', 6: 'juin', 7: 'juillet', 8: 'août',
        9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    try:
        dt = pd.to_datetime(value)
        day = dt.day
        month = months[dt.month]
        year = dt.year
        return f"{day} {month} {year}"
    except (ValueError, TypeError):
        return str(value)

# Application du format date sur les colonnes concernées
def format_date_columns(df):
    if df.empty:
        return df
    df_formatted = df.copy()
    date_keywords = ["date", "naissance", "debut", "fin", "mois", "annee", "année"]
    for col in df_formatted.columns:
        if any(keyword in col.lower() for keyword in date_keywords) or pd.api.types.is_datetime64_any_dtype(df[col]):
            df_formatted[col] = df_formatted[col].apply(format_french_date)
    return df_formatted

# Fonction combinée : monétaire + dates
def format_df(df):
    df = format_monetary_columns(df)
    df = format_date_columns(df)
    return df

# ────────────────────────────────────────────────
#  Section Uploads (visible seulement au démarrage)
# ────────────────────────────────────────────────
if not st.session_state.files_loaded:
    st.header("🚀 Préparation des fichiers")

    uploaded_excel      = st.file_uploader("📂 Charger le fichier Excel RH", type=["xlsx"], key="excel_uploader")
    uploaded_zip_photos  = st.file_uploader("📂 Charger les photos des employés (.zip)", type=["zip"], key="photos_uploader")
    uploaded_zip_cvs    = st.file_uploader("📂 Charger les CV des employés (.zip)", type=["zip"], key="cvs_uploader")

    if st.button("✅ Vérifier et démarrer l'application"):
        all_uploaded = uploaded_excel is not None and uploaded_zip_photos is not None and uploaded_zip_cvs is not None

        if all_uploaded:
            try:
                # Extraction des ZIP
                with zipfile.ZipFile(uploaded_zip_photos, 'r') as zip_ref:
                    zip_ref.extractall('temp_photos')
                with zipfile.ZipFile(uploaded_zip_cvs, 'r') as zip_ref:
                    zip_ref.extractall('temp_cvs')

                # Lecture du fichier Excel
                xls = pd.ExcelFile(uploaded_excel)
                data = {sheet: pd.read_excel(xls, sheet) for sheet in xls.sheet_names}

                # Calcul du nombre total d'employés
                identité = data.get("Identité", pd.DataFrame())
                poste = data.get("Poste_et_Carrière", pd.DataFrame())
                if not identité.empty and not poste.empty:
                    merged_global = pd.merge(identité, poste, on="Matricule", how="inner")
                    total_employes = len(merged_global)
                else:
                    total_employes = 0

                st.session_state.files_loaded = True
                st.session_state.data = data
                st.session_state.total_employes = total_employes

                st.success("✅ Tous les fichiers ont été chargés avec succès ! L'application démarre...")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Erreur lors du chargement des fichiers : {e}")
        else:
            st.warning("⚠️ Veuillez charger les trois fichiers (Excel + ZIP Photos + ZIP CVs) avant de continuer.")

else:
    # ────────────────────────────────────────────────
    #  Application principale (après chargement)
    # ────────────────────────────────────────────────
    st.header("🚀 Gestion des Ressources Humaines – OMNIS")

    data = st.session_state.data
    total_employes = st.session_state.total_employes

    identité    = data.get("Identité", pd.DataFrame())
    poste       = data.get("Poste_et_Carrière", pd.DataFrame())
    salaire     = data.get("Salaire", pd.DataFrame())
    historique  = data.get("Historique", pd.DataFrame())
    presences   = data.get("Présences_Absences", pd.DataFrame())
    missions    = data.get("Missions", pd.DataFrame())
    evaluations = data.get("Évaluations", pd.DataFrame())
    formations  = data.get("Formations", pd.DataFrame())
    turnover    = data.get("Turnover", pd.DataFrame())

    # Recalcul au cas où (cohérence)
    if not identité.empty and not poste.empty:
        merged_global = pd.merge(identité, poste, on="Matricule", how="inner")
        total_employes = len(merged_global)

    # Mapping Direction → Départements
    directions_mapping = {
        'Direction Générale': [
            'Conseiller DG',
            'Direction des affaires juridiques et promotion',
            'DGA Management',
            'DGA Technique',
            'Cellule environnement',
            'Cellule audit et organisation',
            'Cellule analyse des marchés énergie'
        ],

        'DGA Management': [
            'Direction des ressources humaines',
            'Direction administrative et financière',
            'Direction du patrimoine et logistique',
            'Direction système d’information'
        ],

        'DGA Technique': [
            'Direction mine et forage',
            'Direction des hydrocarbures',
            'Direction laboratoire'
        ],

        'Direction des affaires juridiques et promotion': [
            'AD Direction des affaires juridiques et promotion',
            'Département stratégie',
            'Département juridique',
            'Département promotion',
            'Département communication'
        ],

        'Cellule audit et organisation': [
            'Auditeur'
        ],

        'Cellule analyse des marchés énergie': [
            'Responsable suivi et évaluation des projets'
        ],

        'Direction des ressources humaines': [
            'AD Direction des ressources humaines',
            'Département Administration du personnel',
            'Département socio-culturel et événementiel',
            'Département Paie',
            'Département Gestion des carrières et compétences',
            'Département Sécurité',
            'Cellule médecin et conseil'
        ],

        'Direction administrative et financière': [
            'AD Direction administrative et financière',
            'Département Analytique et budget',
            'Département Trésorerie et finance',
            'Département Comptabilité générale'
        ],

        'Direction du patrimoine et logistique': [
            'AD Direction du patrimoine et logistique',
            'Département Approvisionnements',
            'Département Magasins généraux',
            'Département Transport et maintenance',
            'Département Affaires extérieures'
        ],

        'Direction système d’information': [
            'AD Direction système d’information',
            'Département Études',
            'Département Administration réseaux, serveurs et architecture',
            'Département Parc informatique et support'
        ],

        'Direction mine et forage': [
            'AD Direction mine et forage',
            'Département Suivi exploration minière',
            'Département Base de données',
            'Département Gestion du portefeuille minier',
            'Département Forage et prestations',
            'Département Études économiques et financières'
        ],

        'Direction des hydrocarbures': [
            'AD Direction des hydrocarbures',
            'Département Étude bassin Morondava',
            'Département Étude bassin Nord et côte Est',
            'Département Suivi HSE',
            'Département Gestion de la base de données'
        ],

        'Direction laboratoire': [
            'AD Direction laboratoire',
            'Département Gestion administration et projets',
            'Département Contrôle qualité',
            'Département Pétrologie sédimentaire',
            'Département Analyses',
            'Département Géochimie physico-chimie',
            'Département Traitement'
        ]
    }

    tab1, tab2, tab3 = st.tabs(["📊 Tableau de bord général", "🏢 Analyse par direction", "👤 Analyse individuelle"])

    with tab1:
        st.header("📊 Tableau de bord général")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("👥 Total employés", total_employes)
        with col2:
            if not turnover.empty:
                taux_turn = (len(turnover) / total_employes * 100) if total_employes > 0 else 0
                st.metric("📉 Taux de turnover", f"{taux_turn:.1f} %")
        with col3:
            if not salaire.empty:
                salaire["Salaire_Brut"] = pd.to_numeric(salaire["Salaire_Brut"], errors="coerce")
                avg_brut = salaire["Salaire_Brut"].mean()
                st.metric("💵 Salaire moyen brut", format_ar(avg_brut))
        with col4:
            if not presences.empty:
                absent_rate = (len(presences[presences["Type"] != "Présence"]) / len(presences) * 100) if len(presences) > 0 else 0
                st.metric("📅 Taux d'absentéisme", f"{absent_rate:.1f} %")
        with col5:
            if not identité.empty and "Sexe" in identité.columns:
                hf = (len(identité[identité["Sexe"] == "Femme"]) / total_employes * 100) if total_employes > 0 else 0
                st.metric("👩‍💼 Diversité H/F", f"{hf:.1f} % de femmes")

        if not salaire.empty:
            st.subheader("💰 Dépenses salariales totales")
            salaire["Salaire_Brut"] = pd.to_numeric(salaire["Salaire_Brut"], errors="coerce")
            monthly_total = salaire.groupby("Mois")["Salaire_Brut"].sum().reset_index()
            monthly_total['Salaire_Brut'] = monthly_total['Salaire_Brut'].apply(lambda x: x / 1000000)
            fig_bar_monthly = px.bar(monthly_total, x="Mois", y="Salaire_Brut",
                                     title="Dépenses totales par mois (en millions Ar)")
            fig_bar_monthly.update_traces(hovertemplate='%{x}: %{y:.2f} M Ar<extra></extra>')
            fig_bar_monthly.update_yaxes(tickformat=".2f", title="Millions Ar")
            st.plotly_chart(fig_bar_monthly, use_container_width=True)
            total_global = salaire["Salaire_Brut"].sum()
            st.metric("💵 Dépenses totales globales", format_ar(total_global))

        if not identité.empty and "Sexe" in identité.columns:
            st.subheader("👥 Répartition Hommes / Femmes")
            hf_dist = identité["Sexe"].value_counts()
            fig_hf = px.pie(values=hf_dist.values, names=hf_dist.index, title="Répartition globale H/F")
            st.plotly_chart(fig_hf, use_container_width=True)

        if not turnover.empty:
            st.subheader("🔄 Turnover global")
            if "Motif" in turnover.columns:
                motif_dist = turnover["Motif"].value_counts()
                fig_turn = px.bar(x=motif_dist.index, y=motif_dist.values, title="Motifs de départ")
                st.plotly_chart(fig_turn, use_container_width=True)

    with tab2:
        st.header("🏢 Analyse par direction")

        if "Direction" in poste.columns:
            selected_dir = st.selectbox("Filtrer par direction", ["Tous"] + sorted(poste["Direction"].dropna().unique().tolist()))
        else:
            selected_dir = "Tous"

        available_depts = directions_mapping.get(selected_dir, []) if selected_dir != "Tous" else sorted(poste["Département"].dropna().unique().tolist())
        selected_depts = st.multiselect("Filtrer par départements (liés à la direction)", available_depts, default=[])

        filtered_poste = poste.copy()
        if selected_dir != "Tous":
            filtered_poste = filtered_poste[filtered_poste["Direction"] == selected_dir]
        if selected_depts:
            filtered_poste = filtered_poste[filtered_poste["Département"].isin(selected_depts)]

        if not filtered_poste.empty:
            ids_filtered = filtered_poste["Matricule"].tolist()
            salaire_filt = salaire[salaire["Matricule"].isin(ids_filtered)] if not salaire.empty else pd.DataFrame()

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Employés filtrés", len(filtered_poste))
            with col2:
                if not salaire_filt.empty:
                    salaire_filt["Salaire_Brut"] = pd.to_numeric(salaire_filt["Salaire_Brut"], errors="coerce")
                    avg_salaire = salaire_filt["Salaire_Brut"].mean()
                    st.metric("💵 Salaire moyen", format_ar(avg_salaire))
                else:
                    st.metric("💵 Salaire moyen", "N/A")
            with col3:
                if not salaire_filt.empty:
                    total_salaire = salaire_filt["Salaire_Brut"].sum()
                    st.metric("💼 Masse salariale totale", format_ar(total_salaire))
                else:
                    st.metric("💼 Masse salariale totale", "N/A")
            with col4:
                if not salaire_filt.empty and "Mois" in salaire_filt.columns:
                    total_salaire = salaire_filt["Salaire_Brut"].sum()
                    nb_mois = salaire_filt["Mois"].nunique()
                    if nb_mois > 0:
                        masse_moyenne_mois = total_salaire / nb_mois
                        st.metric("💰 Masse salariale moyenne/mois", format_ar(masse_moyenne_mois))
                    else:
                        st.metric("💰 Masse salariale moyenne/mois", "N/A")
                else:
                    st.metric("💰 Masse salariale moyenne/mois", "N/A")

            if not salaire_filt.empty and "Mois" in salaire_filt.columns:
                monthly_filt = salaire_filt.groupby("Mois")["Salaire_Brut"].sum().reset_index()
                monthly_filt['Salaire_Brut'] = monthly_filt['Salaire_Brut'].apply(lambda x: x / 1000000)
                fig_bar_filt = px.bar(monthly_filt, x="Mois", y="Salaire_Brut",
                                      title="Dépenses salariales filtrées par mois (en millions Ar)")
                fig_bar_filt.update_traces(hovertemplate='%{x}: %{y:.2f} M Ar<extra></extra>')
                fig_bar_filt.update_yaxes(tickformat=".2f", title="Millions Ar")
                st.plotly_chart(fig_bar_filt, use_container_width=True)

            ident_filt = identité[identité["Matricule"].isin(ids_filtered)] if not identité.empty else pd.DataFrame()
            if not ident_filt.empty and "Sexe" in ident_filt.columns:
                hf_filt = ident_filt["Sexe"].value_counts()
                fig_hf_filt = px.pie(values=hf_filt.values, names=hf_filt.index, title="Répartition H/F – Direction sélectionnée")
                st.plotly_chart(fig_hf_filt, use_container_width=True)

            turnover_filt = turnover[turnover["Matricule"].isin(ids_filtered)] if not turnover.empty else pd.DataFrame()
            if not turnover_filt.empty and "Motif" in turnover_filt.columns:
                motif_filt = turnover_filt["Motif"].value_counts()
                fig_turn_filt = px.bar(x=motif_filt.index, y=motif_filt.values, title="Motifs de départ – Direction sélectionnée")
                st.plotly_chart(fig_turn_filt, use_container_width=True)
        else:
            st.warning("Aucun employé ne correspond aux filtres appliqués.")

    with tab3:
        st.header("👤 Analyse individuelle")

        search_term = st.text_input("🔍 Rechercher par matricule ou nom")
        selected_id = None
        if search_term and not identité.empty:
            mask_id = identité["Matricule"].astype(str).str.contains(search_term, case=False, na=False)
            mask_nom = identité["Nom"].str.contains(search_term, case=False, na=False)
            filtered = identité[mask_id | mask_nom]
            if not filtered.empty:
                selected_id = st.selectbox("Choisir un matricule", filtered["Matricule"].tolist())

        if selected_id:
            emp_poste = poste[poste["Matricule"] == selected_id]
            emp_ident = identité[identité["Matricule"] == selected_id]
            emp_data = {k: v[v["Matricule"] == selected_id] for k, v in data.items() if "Matricule" in v.columns}

            st.subheader("🖼️ Photo d’identité")
            photo_path = f"temp_photos/photo_{selected_id}.jpg"
            if os.path.exists(photo_path):
                image = Image.open(photo_path)
                st.image(image, caption=f"Photo – Matricule {selected_id}", width=200)
            else:
                st.warning("⚠️ Aucune photo trouvée pour ce matricule. Vérifiez le contenu du ZIP.")

            st.subheader("📋 Profil de l’employé")
            if not emp_poste.empty and not emp_ident.empty:
                row_poste = emp_poste.iloc[0]
                row_ident = emp_ident.iloc[0]
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Nom :** {row_ident.get('Nom', 'N/A')} {row_ident.get('Prénom', 'N/A')}")
                    age = int((datetime.now() - pd.to_datetime(row_ident.get('Date_Naissance', datetime.now()))).days // 365)
                    st.write(f"**Âge :** {age} ans")
                    st.write(f"**Direction :** {row_poste.get('Direction', 'N/A')}")
                    st.write(f"**Département :** {row_poste.get('Département', 'N/A')}")
                    st.write(f"**Poste actuel :** {row_poste.get('Poste_Actuel', 'N/A')}")
                with col2:
                    st.write(f"**Années d’expérience dans la société :** {row_poste.get('Ancienneté', 'N/A')} ans")
                    st.write(f"**Sexe :** {row_ident.get('Sexe', 'N/A')}")
                    st.write(f"**Niveau d’études :** {row_ident.get('Niveau_études', 'N/A')}")
                    st.write(f"**Compétences clés :** {row_ident.get('Compétences_clés', 'N/A')}")
                    if "Salaire" in emp_data and not emp_data["Salaire"].empty and "Mois" in emp_data["Salaire"].columns:
                        emp_salaire = emp_data["Salaire"]
                        emp_salaire["Salaire_Brut"] = pd.to_numeric(emp_salaire["Salaire_Brut"], errors="coerce")
                        total_salaire_emp = emp_salaire["Salaire_Brut"].sum()
                        nb_mois_emp = emp_salaire["Mois"].nunique()
                        if nb_mois_emp > 0:
                            salaire_moyen_mois = total_salaire_emp / nb_mois_emp
                            st.write(f"**💵 Salaire moyen par mois :** {format_ar(salaire_moyen_mois)}")
                        else:
                            st.write("**💵 Salaire moyen par mois :** N/A")
                    else:
                        st.write("**💵 Salaire moyen par mois :** N/A")

                cv_path = f"temp_cvs/cv_{selected_id}.pdf"
                if os.path.exists(cv_path):
                    with open(cv_path, "rb") as file:
                        st.download_button(
                            label=f"📄 Voir / Télécharger le CV (Matricule {selected_id})",
                            data=file.read(),
                            file_name=f"cv_{selected_id}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.warning("⚠️ Aucun CV trouvé pour ce matricule. Vérifiez le contenu du ZIP CVs.")

            if "Évaluations" in emp_data and not emp_data["Évaluations"].empty:
                st.subheader("📊 Évaluations annuelles")
                df_eval_formatted = format_df(emp_data["Évaluations"])
                st.dataframe(df_eval_formatted, use_container_width=True)

            if "Formations" in emp_data and not emp_data["Formations"].empty:
                st.subheader("🎓 Formations")
                df_form_formatted = format_df(emp_data["Formations"])
                st.dataframe(df_form_formatted, use_container_width=True)

            if "Missions" in emp_data and not emp_data["Missions"].empty:
                st.subheader("🎯 Missions")
                df_miss = emp_data["Missions"]
                df_miss_formatted = format_df(df_miss)
                nb_actives = len(df_miss[df_miss["Statut"] == "En cours"])
                st.metric("📊 Nombre de missions actives", nb_actives)
                st.dataframe(df_miss_formatted, use_container_width=True)
            else:
                st.info("Aucune mission enregistrée pour cet employé.")

            if "Présences_Absences" in emp_data and not emp_data["Présences_Absences"].empty:
                st.subheader("📅 Présences / Absences")
                df_abs = emp_data["Présences_Absences"].head(10)
                df_abs_formatted = format_df(df_abs)
                if "Congé_restant" in df_abs.columns:
                    st.write(f"**Congés restants :** {df_abs['Congé_restant'].iloc[0]} jours")
                st.dataframe(df_abs_formatted, use_container_width=True)

            if "Historique" in emp_data and not emp_data["Historique"].empty:
                st.subheader("📈 Historique complet (sanctions, bonus, évolutions, etc.)")
                df_hist_formatted = format_df(emp_data["Historique"])
                st.dataframe(df_hist_formatted, use_container_width=True)

    if st.button("🗑️ Supprimer les dossiers temporaires (photos & CV)"):
        if os.path.exists('temp_photos'):
            shutil.rmtree('temp_photos')
        if os.path.exists('temp_cvs'):
            shutil.rmtree('temp_cvs')
        st.success("Dossiers temporaires supprimés avec succès.")

# Footer
st.markdown("---")
st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #f8f9fa;
    text-align: center;
    padding: 12px;
    z-index: 1000;
    font-size: 1.1rem;
    color: #555;
    border-top: 1px solid #ddd;
}
</style>
<div class="footer">
    <strong>Outil créé par RANAIVOSOA Tojoarimanana Hiratriniala</strong><br>
    Tél : +261 33 51 880 19
</div>
""", unsafe_allow_html=True)
