import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Assistant IA RH", page_icon="🤖")

st.title("🤖 Assistant IA RH")
st.markdown("Bienvenue dans votre assistant RH intelligent.")

# Sidebar pour les informations de l'utilisateur
st.sidebar.header("Paramètres Utilisateur")
user_id = st.sidebar.number_input("ID Utilisateur", min_value=1, value=1)
role = st.sidebar.selectbox("Rôle", ["collaborateur", "manager", "rh", "admin"])

# Onglets pour les différentes fonctionnalités
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📄 Génération de Document", "📊 Supervision"])

with tab1:
    st.header("Posez votre question RH")
    question = st.text_input("Votre question :", placeholder="ex: Combien de jours de congés me reste-t-il ?")
    
    if st.button("Envoyer"):
        if question:
            with st.spinner("L'assistant réfléchit..."):
                try:
                    response = requests.post(f"{API_URL}/chat", json={
                        "user_id": user_id,
                        "role": role,
                        "question": question
                    })
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success":
                            st.success("Réponse trouvée !")
                            st.info(f"**Intention détectée :** {data.get('intent')}")
                            st.write(data.get("answer"))
                        else:
                            st.error("Accès refusé ou erreur.")
                            st.write(data.get("answer"))
                    else:
                        st.error(f"Erreur de l'API: {response.status_code}")
                except Exception as e:
                    st.error(f"Impossible de contacter l'API. Assurez-vous qu'elle est lancée. ({e})")
        else:
            st.warning("Veuillez entrer une question.")

with tab2:
    st.header("Génération de Documents RH")
    doc_type = st.selectbox("Type de document", ["attestation_employeur", "contrat_travail", "avenant", "solde_tout_compte"])
    
    if st.button("Générer le document"):
        with st.spinner("Génération en cours..."):
            try:
                response = requests.post(f"{API_URL}/generate-document", json={
                    "user_id": user_id,
                    "role": role,
                    "document_type": doc_type
                })
                if response.status_code == 200:
                    data = response.json()
                    st.json(data)
                else:
                    st.error(f"Erreur de l'API: {response.status_code}")
            except Exception as e:
                st.error(f"Impossible de contacter l'API. ({e})")

with tab3:
    st.header("Supervision")
    if st.button("Actualiser les logs"):
        try:
            logs_response = requests.get(f"{API_URL}/supervision/logs")
            if logs_response.status_code == 200:
                st.subheader("Derniers Logs")
                st.json(logs_response.json())
            else:
                st.error("Erreur lors de la récupération des logs.")
                
            alerts_response = requests.get(f"{API_URL}/supervision/alerts")
            if alerts_response.status_code == 200:
                st.subheader("Alertes de Sécurité")
                st.json(alerts_response.json())
            else:
                st.error("Erreur lors de la récupération des alertes.")
        except Exception as e:
            st.error(f"Impossible de contacter l'API. ({e})")
