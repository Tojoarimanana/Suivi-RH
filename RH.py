import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import zipfile
import os
import shutil
from PIL import Image

st.set_page_config(page_title="Application Web RH-OMNIS", layout="wide")

st.title("📋 Gestion RH OMNIS ")

# Initialiser session_state pour tracker les uploads
if 'files_loaded' not in st.session_state:
    st.session_state.files_loaded = False
if 'data' not in st.session_state:
    st.session_state.data = None
if 'total_employes' not in st.session_state:
    st.session_state.total_employes = 0

# Fonction pour formater les montants en Ar avec espace comme séparateur de milliers
def format_ar(value):
    if pd.isna(value):
        return "N/A"
    # Convertir en numeric si nécessaire
    try:
        value = float(value)
    except (ValueError, TypeError):
        return str(value)
    formatted = f"{value:,.2f}".replace(",", " ")
    return f"{formatted} Ar"

# Fonction pour formater un dataframe (colonnes monétaires)
def format_monetary_columns(df):
    if df.empty:
        return df
    df_formatted = df.copy()
    monetary_keywords = ["salaire", "bonus", "montant", "prime", "indemnité", "sanction", "coût", "cout", "depense", "dépense"]  # Ajouté pour les coûts
    for col in df_formatted.columns:
        if any(keyword in col.lower() for keyword in monetary_keywords):
            df_formatted[col] = pd.to_numeric(df_formatted[col], errors='coerce')
            df_formatted[col] = df_formatted[col].apply(format_ar)
    return df_formatted

# Fonction pour formater les dates en français (ex: "22 janvier 2025")
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

# Fonction pour formater les colonnes de dates (sans heure, juste la date en français)
def format_date_columns(df):
    if df.empty:
        return df
    df_formatted = df.copy()
    date_keywords = ["date", "naissance", "debut", "fin", "mois", "annee", "anneé"]  # Mots-clés pour détecter les dates
    for col in df_formatted.columns:
        if any(keyword in col.lower() for keyword in date_keywords) or pd.api.types.is_datetime64_any_dtype(df[col]):
            df_formatted[col] = df_formatted[col].apply(format_french_date)
    return df_formatted

# Fonction combinée pour formater un dataframe (monétaire + dates)
def format_df(df):
    df = format_monetary_columns(df)
    df = format_date_columns(df)
    return df

# Section Uploads (visible seulement si pas encore chargé)
if not st.session_state.files_loaded:
    st.header("🚀 Préparation des Fichiers")
    
    # Upload Excel, ZIP Photos ET ZIP CVs
    uploaded_excel = st.file_uploader("📂 Charger Donnée Excel RH", type=["xlsx"], key="excel_uploader")
    uploaded_zip_photos = st.file_uploader("📂 Charger Photos des employés .ZIP", type=["zip"], key="photos_uploader")
    uploaded_zip_cvs = st.file_uploader("📂 Charger  CVs des employés .ZIP", type=["zip"], key="cvs_uploader")

    # Bouton Vérifier et Démarrer
    if st.button("✅ Vérifier et Démarrer l'App"):
        all_uploaded = uploaded_excel is not None and uploaded_zip_photos is not None and uploaded_zip_cvs is not None
        
        if all_uploaded:
            try:
                # Extraction ZIPs
                with zipfile.ZipFile(uploaded_zip_photos, 'r') as zip_ref:
                    zip_ref.extractall('temp_photos')
                with zipfile.ZipFile(uploaded_zip_cvs, 'r') as zip_ref:
                    zip_ref.extractall('temp_cvs')
                
                # Chargement Excel
                xls = pd.ExcelFile(uploaded_excel)
                data = {sheet: pd.read_excel(xls, sheet) for sheet in xls.sheet_names}
                
                # Calcul total employés
                identité = data.get("Identité", pd.DataFrame())
                poste = data.get("Poste_et_Carrière", pd.DataFrame())
                if not identité.empty and not poste.empty:
                    merged_global = pd.merge(identité, poste, on="Matricule", how="inner")
                    total_employes = len(merged_global)
                else:
                    total_employes = 0
                
                # Stocker en session_state
                st.session_state.files_loaded = True
                st.session_state.data = data
                st.session_state.total_employes = total_employes
                
                st.success("✅ Tous les fichiers chargés ! L'app démarre...")
                st.rerun()  # Refresh pour masquer uploads
                
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement : {e}")
        else:
            st.warning("⚠️ Chargez tous les fichiers (Excel + ZIP Photos + ZIP CVs) avant de démarrer.")

else:

# App principale (uploads masqués)
    st.header("🚀 Géstion des ressources Humaines de l'OMNIS – Bienvenue !")
    
    # Récupérer data de session_state
    data = st.session_state.data
    total_employes = st.session_state.total_employes
    identité = data.get("Identité", pd.DataFrame())
    poste = data.get("Poste_et_Carrière", pd.DataFrame())
    salaire = data.get("Salaire", pd.DataFrame())
    historique = data.get("Historique", pd.DataFrame())
    presences = data.get("Présences_Absences", pd.DataFrame())
    missions = data.get("Missions", pd.DataFrame())
    evaluations = data.get("Évaluations", pd.DataFrame())
    formations = data.get("Formations", pd.DataFrame())
    turnover = data.get("Turnover", pd.DataFrame())

    # Fusion globale pour total employés
    if not identité.empty and not poste.empty:
        merged_global = pd.merge(identité, poste, on="Matricule", how="inner")
        total_employes = len(merged_global)
    else:
        total_employes = 0

    # Directions mapping for logical filter
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

    tab1, tab2, tab3 = st.tabs(["📊 Tableau de Bord Général", "🏢 Analyse par Direction", "👤 Analyse Individuelle"])

    with tab1:
        st.header("📊 Tableau de Bord Général")
        
        # Metrics dynamiques (sans TBD)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("👥 Total Employés", total_employes)
        with col2:
            if not turnover.empty:
                taux_turn = (len(turnover) / total_employes * 100) if total_employes > 0 else 0
                st.metric("📉 Turnover %", f"{taux_turn:.1f}%")
        with col3:
            if not salaire.empty:
                salaire["Salaire_Brut"] = pd.to_numeric(salaire["Salaire_Brut"], errors="coerce")
                avg_brut = salaire["Salaire_Brut"].mean()
                st.metric("💵 Salaire Moyen Brut", format_ar(avg_brut))
        with col4:
            if not presences.empty:
                absent_rate = (len(presences[presences["Type"] != "Présence"]) / len(presences) * 100) if len(presences) > 0 else 0
                st.metric("📅 Absentéisme %", f"{absent_rate:.1f}%")
        with col5:
            if not identité.empty and "Sexe" in identité.columns:
                hf = (len(identité[identité["Sexe"] == "Femme"]) / total_employes * 100) if total_employes > 0 else 0
                st.metric("👩‍💼 Diversité H/F %", f"{hf:.1f}% Femmes")

        # Salaires: Total dépenses en bar graph mensuel
        if not salaire.empty:
            st.subheader("💰 Dépenses Salariales Totales")
            salaire["Salaire_Brut"] = pd.to_numeric(salaire["Salaire_Brut"], errors="coerce")
            monthly_total = salaire.groupby("Mois")["Salaire_Brut"].sum().reset_index()
            # Formater les valeurs y pour l'affichage (diviser par 1000 pour 'k' et ajuster)
            monthly_total['Salaire_Brut'] = monthly_total['Salaire_Brut'].apply(lambda x: x / 1000000)  # En millions pour simplicité
            fig_bar_monthly = px.bar(monthly_total, x="Mois", y="Salaire_Brut", title="Dépenses Totales par Mois (en millions Ar)")
            fig_bar_monthly.update_traces(hovertemplate='%{x}: %{y:.2f}M Ar<extra></extra>')
            fig_bar_monthly.update_yaxes(tickformat=".2f", title="Millions Ar")
            st.plotly_chart(fig_bar_monthly, use_container_width=True)
            total_global = salaire["Salaire_Brut"].sum()
            st.metric("💵 Dépenses Totales Globales", format_ar(total_global))

        # Répartition H/F
        if not identité.empty and "Sexe" in identité.columns:
            st.subheader("👥 Répartition Hommes/Femmes")
            hf_dist = identité["Sexe"].value_counts()
            fig_hf = px.pie(values=hf_dist.values, names=hf_dist.index, title="Répartition Globale H/F")
            st.plotly_chart(fig_hf, use_container_width=True)

        # Turnover
        if not turnover.empty:
            st.subheader("🔄 Turnover Global")
            if "Motif" in turnover.columns:
                motif_dist = turnover["Motif"].value_counts()
                fig_turn = px.bar(x=motif_dist.index, y=motif_dist.values, title="Motifs de Départ")
                st.plotly_chart(fig_turn, use_container_width=True)

    with tab2:
        st.header("🏢 Analyse par Direction")
        
        # Filtres logiques
        if "Direction" in poste.columns:
            selected_dir = st.selectbox("Filtrer par Direction", ["Tous"] + sorted(poste["Direction"].dropna().unique().tolist()))
        else:
            selected_dir = "Tous"

        # Multi-select Départements liés à la Direction
        available_depts = directions_mapping.get(selected_dir, []) if selected_dir != "Tous" else sorted(poste["Département"].dropna().unique().tolist())
        selected_depts = st.multiselect("Filtrer par Départements (liés à la Direction)", available_depts, default=[])

        # Filtrage
        filtered_poste = poste.copy()
        if selected_dir != "Tous":
            filtered_poste = filtered_poste[filtered_poste["Direction"] == selected_dir]
        if selected_depts:
            filtered_poste = filtered_poste[filtered_poste["Département"].isin(selected_depts)]

        if not filtered_poste.empty:
            ids_filtered = filtered_poste["Matricule"].tolist()
            salaire_filt = salaire[salaire["Matricule"].isin(ids_filtered)] if not salaire.empty else pd.DataFrame()

            # Metrics (AJOUT : 4 colonnes pour inclure la moyenne mensuelle)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Employés Filtrés", len(filtered_poste))
            with col2:
                if not salaire_filt.empty:
                    salaire_filt["Salaire_Brut"] = pd.to_numeric(salaire_filt["Salaire_Brut"], errors="coerce")
                    avg_salaire = salaire_filt["Salaire_Brut"].mean()
                    st.metric("💵 Salaire Moyen", format_ar(avg_salaire))
                else:
                    st.metric("💵 Salaire Moyen", "N/A")
            with col3:
                if not salaire_filt.empty:
                    total_salaire = salaire_filt["Salaire_Brut"].sum()
                    st.metric("💼 Masse Salariale Totale", format_ar(total_salaire))
                else:
                    st.metric("💼 Masse Salariale Totale", "N/A")
            # NOUVEAU KPI : Masse salariale moyenne par mois
            with col4:
                if not salaire_filt.empty and "Mois" in salaire_filt.columns:
                    # Calcul : Somme totale / Nombre de mois distincts
                    total_salaire = salaire_filt["Salaire_Brut"].sum()
                    nb_mois = salaire_filt["Mois"].nunique()  # Nombre de mois uniques
                    if nb_mois > 0:
                        masse_moyenne_mois = total_salaire / nb_mois
                        st.metric("💰 Masse Salariale Moyenne/Mois", format_ar(masse_moyenne_mois))
                    else:
                        st.metric("💰 Masse Salariale Moyenne/Mois", "N/A")
                else:
                    st.metric("💰 Masse Salariale Moyenne/Mois", "N/A")

            # Salaires filtrés (bar mensuel)
            if not salaire_filt.empty and "Mois" in salaire_filt.columns:
                monthly_filt = salaire_filt.groupby("Mois")["Salaire_Brut"].sum().reset_index()
                # Formater similairement pour le graphique
                monthly_filt['Salaire_Brut'] = monthly_filt['Salaire_Brut'].apply(lambda x: x / 1000000)
                fig_bar_filt = px.bar(monthly_filt, x="Mois", y="Salaire_Brut", title="Dépenses Salariales Filtrées par Mois (en millions Ar)")
                fig_bar_filt.update_traces(hovertemplate='%{x}: %{y:.2f}M Ar<extra></extra>')
                fig_bar_filt.update_yaxes(tickformat=".2f", title="Millions Ar")
                st.plotly_chart(fig_bar_filt, use_container_width=True)

            # Répartition H/F filtrée
            ident_filt = identité[identité["Matricule"].isin(ids_filtered)] if not identité.empty else pd.DataFrame()
            if not ident_filt.empty and "Sexe" in ident_filt.columns:
                hf_filt = ident_filt["Sexe"].value_counts()
                fig_hf_filt = px.pie(values=hf_filt.values, names=hf_filt.index, title="Répartition H/F ")
                st.plotly_chart(fig_hf_filt, use_container_width=True)

            # Turnover filtré
            turnover_filt = turnover[turnover["Matricule"].isin(ids_filtered)] if not turnover.empty else pd.DataFrame()
            if not turnover_filt.empty and "Motif" in turnover_filt.columns:
                motif_filt = turnover_filt["Motif"].value_counts()
                fig_turn_filt = px.bar(x=motif_filt.index, y=motif_filt.values, title="Turnover ")
                st.plotly_chart(fig_turn_filt, use_container_width=True)
        else:
            st.warning("Aucun filtre appliqué ou données vides.")

    with tab3:
        st.header("👤 Analyse Individuelle")
        
        # Filtre recherche
        search_term = st.text_input("🔍 Rechercher par Matricule ou Nom")
        selected_id = None
        if search_term and not identité.empty:
            mask_id = identité["Matricule"].astype(str).str.contains(search_term, case=False, na=False)
            mask_nom = identité["Nom"].str.contains(search_term, case=False, na=False)
            filtered = identité[mask_id | mask_nom]
            if not filtered.empty:
                selected_id = st.selectbox("Choisir Matricule", filtered["Matricule"].tolist())

        if selected_id:
            # Fusion pour employé
            emp_poste = poste[poste["Matricule"] == selected_id]
            emp_ident = identité[identité["Matricule"] == selected_id]
            emp_data = {k: v[v["Matricule"] == selected_id] for k, v in data.items() if "Matricule" in v.columns}

            # Photo (liée à ID)
            st.subheader("🖼️ Photo d'Identité")
            photo_path = f"temp_photos/photo_{selected_id}.jpg"
            if os.path.exists(photo_path):
                image = Image.open(photo_path)
                st.image(image, caption=f"Photo Matricule {selected_id}", width=200)
            else:
                st.warning("⚠️ Pas de photo trouvée pour cet Matricule. Vérifiez le ZIP.")

            # Profile étendu + Bouton CV (téléchargement qui ouvre externe)
            st.subheader("📋 Profil de l'employé")
            if not emp_poste.empty and not emp_ident.empty:
                row_poste = emp_poste.iloc[0]
                row_ident = emp_ident.iloc[0]
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Nom :** {row_ident.get('Nom', 'N/A')} {row_ident.get('Prénom', 'N/A')}")
                    # MODIFIÉ : Ajout de l'unité " ans" pour l'âge
                    age = int((datetime.now() - pd.to_datetime(row_ident.get('Date_Naissance', datetime.now()))).days // 365)
                    st.write(f"**Âge :** {age} ans")
                    st.write(f"**Direction :** {row_poste.get('Direction', 'N/A')}")
                    st.write(f"**Département :** {row_poste.get('Département', 'N/A')}")
                    st.write(f"**Poste :** {row_poste.get('Poste_Actuel', 'N/A')}")
                with col2:
                    st.write(f"**Années d'Expérience Société :** {row_poste.get('Ancienneté', 'N/A')} ans")
                    st.write(f"**Sexe :** {row_ident.get('Sexe', 'N/A')}")
                    st.write(f"**Niveau d'Études :** {row_ident.get('Niveau_études', 'N/A')}")
                    st.write(f"**Compétences :** {row_ident.get('Compétences_clés', 'N/A')}")
                    # NOUVEAU : Salaire moyen par mois pour cet employé
                    if "Salaire" in emp_data and not emp_data["Salaire"].empty and "Mois" in emp_data["Salaire"].columns:
                        emp_salaire = emp_data["Salaire"]
                        emp_salaire["Salaire_Brut"] = pd.to_numeric(emp_salaire["Salaire_Brut"], errors="coerce")
                        total_salaire_emp = emp_salaire["Salaire_Brut"].sum()
                        nb_mois_emp = emp_salaire["Mois"].nunique()
                        if nb_mois_emp > 0:
                            salaire_moyen_mois = total_salaire_emp / nb_mois_emp
                            st.write(f"**💵 Salaire Moyen par Mois :** {format_ar(salaire_moyen_mois)}")
                        else:
                            st.write("**💵 Salaire Moyen par Mois :** N/A")
                    else:
                        st.write("**💵 Salaire Moyen par Mois :** N/A")

                # Bouton CV (téléchargement qui ouvre externe)
                cv_path = f"temp_cvs/cv_{selected_id}.pdf"
                if os.path.exists(cv_path):
                    with open(cv_path, "rb") as file:
                        btn = st.download_button(
                            label=f"📄 Voir son CV (Matricule {selected_id})",
                            data=file.read(),
                            file_name=f"cv_{selected_id}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.warning("⚠️ Pas de CV trouvé pour cet Matricule. Vérifiez le ZIP CVs.")

            # Évaluations annu
            if "Évaluations" in emp_data and not emp_data["Évaluations"].empty:
                st.subheader("📊 Évaluations Annuelle")
                df_eval_formatted = format_df(emp_data["Évaluations"])
                st.dataframe(df_eval_formatted, use_container_width=True)

            # Formations 
            if "Formations" in emp_data and not emp_data["Formations"].empty:
                st.subheader("🎓 Formations ")
                df_form_formatted = format_df(emp_data["Formations"])
                st.dataframe(df_form_formatted, use_container_width=True)

            # Missions 
            if "Missions" in emp_data and not emp_data["Missions"].empty:
                st.subheader("🎯 Missions ")
                df_miss = emp_data["Missions"]
                df_miss_formatted = format_df(df_miss)
                nb_actives = len(df_miss[df_miss["Statut"] == "En cours"])
                st.metric("📊 Nombre de Missions Actives", nb_actives)
                st.dataframe(df_miss_formatted, use_container_width=True)
            else:
                st.info("Aucune mission trouvée pour cet employé.")

            # Présences/Absences with Congé restant
            if "Présences_Absences" in emp_data and not emp_data["Présences_Absences"].empty:
                st.subheader("📅 Présences/Absences")
                df_abs = emp_data["Présences_Absences"].head(10)
                df_abs_formatted = format_df(df_abs)
                if "Congé_restant" in df_abs.columns:
                    st.write(f"**Congés Restants :** {df_abs['Congé_restant'].iloc[0]} jours")
                st.dataframe(df_abs_formatted, use_container_width=True)

            # Historique complet
            if "Historique" in emp_data and not emp_data["Historique"].empty:
                st.subheader("📈 Historique Complet (Sanctions, Bonus, Évolution, ...)")
                df_hist_formatted = format_df(emp_data["Historique"])
                st.dataframe(df_hist_formatted, use_container_width=True)

    # Nettoyage temp (optionnel)
    if st.button("🗑️ Nettoyer Dossiers Temp (Photos & CVs)"):
        if os.path.exists('temp_photos'):
            shutil.rmtree('temp_photos')
        if os.path.exists('temp_cvs'):
            shutil.rmtree('temp_cvs')
        st.success("Dossiers temp supprimés.")


st.markdown("---")
st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #f0f0f0;
    text-align: center;
    padding: 10px;
    z-index: 1000;
    font-size: 20px;
    color: #666;
}
</style>
<div class="footer">
    <i style='color:red; font-weight:bold;'> Outils Créé par RANAIVOSOA Tojoarimanana Hiratriniala / Tel: +261 33 51 880 19</i>
</div>
""", unsafe_allow_html=True)