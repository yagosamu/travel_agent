from textwrap import dedent
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
import streamlit as st
from agno.models.openai import OpenAIChat
import re
import requests

# Função para buscar imagem no Unsplash
def buscar_imagem_unsplash(query, unsplash_access_key):
    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "orientation": "landscape",
        "client_id": unsplash_access_key
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data["urls"]["small"]
    except Exception:
        pass
    return ""

st.title("AI Travel Planner ✈️")
st.caption("Plan your next adventure with AI Travel Planner by researching and planning a personalized itinerary on autopilot using GPT-4o")

openai_api_key = st.text_input("Enter OpenAI API Key to access GPT-4o", type="password")
serp_api_key = st.text_input("Enter Serp API Key for Search functionality", type="password")
unsplash_access_key = st.text_input("Enter your Unsplash API Access Key", type="password")

profile_options = {
    "Romântico": "romantic",
    "Aventura": "adventure",
    "Família": "family",
    "Econômico": "budget"
}
profile_human = st.selectbox(
    "Qual o perfil da sua viagem?",
    list(profile_options.keys()),
    index=0
)
profile = profile_options[profile_human]

languages = {
    "Português": "Portuguese",
    "Inglês": "English",
    "Espanhol": "Spanish"
}
language_human = st.selectbox(
    "Selecione o idioma do itinerário:",
    list(languages.keys()),
    index=0
)
language = languages[language_human]

destination = st.text_input("Para onde você quer viajar?")
num_days = st.number_input("Quantos dias de viagem?", min_value=1, max_value=30, value=7)

if openai_api_key and serp_api_key and unsplash_access_key:
    researcher = Agent(
        name="Researcher",
        role="Searches for travel destinations, activities, and accommodations based on user preferences",
        model=OpenAIChat(id="gpt-4o", api_key=openai_api_key),
        description=dedent(
            f"""\
            You are a world-class travel researcher. Given a travel destination, number of days,
            travel profile (such as romantic, adventure, family, or budget), and preferred language,
            generate a list of search terms for finding relevant travel activities and accommodations.
            Search the web for each term, analyze the results, and return the 10 most relevant results.
            All results should be tailored to the user's travel profile and preferences.
            """
        ),
        instructions=[
            "Given a travel destination, number of days, travel profile, and language, first generate a list of 3 search terms related to that destination, duration, and profile.",
            "For each search term, `search_google` and analyze the results.",
            "From the results of all searches, return the 10 most relevant results to the user's preferences.",
            "Remember: the quality and relevance to the travel profile are important.",
        ],
        tools=[SerpApiTools(api_key=serp_api_key)],
        add_datetime_to_instructions=True,
    )

    # PROMPT para o modelo gerar apenas o texto dos dias
    planner_prompt_instructions = dedent(f"""
    Você é um especialista em viagens, responsável por criar roteiros personalizados de alta qualidade para {profile_human} ({profile}) em {language_human}.
    Para cada dia do roteiro, crie um título curto e objetivo para o dia, seguido de uma breve descrição das atividades e experiências desse dia.

    Estruture cada dia exatamente assim (no idioma do usuário):

    Dia X: [Título do dia]
    [Descrição do dia, curta e objetiva, que explique as atividades e experiências.]

    Regras:
    - O título deve ser uma frase curta (exemplo: 'Passeio pelo centro histórico', 'Aventura nas trilhas', 'Dia em família no parque aquático').
    - O texto deve ser sempre claro, objetivo e útil para o viajante, refletindo o perfil da viagem, as preferências do usuário e o idioma escolhido.
    - O roteiro deve ser visualmente organizado e fácil de ler, com cada dia separado pelo cabeçalho “Dia X: [Título]”.

    Exemplo de resposta para um dia (em português):

    Dia 1: Passeio pelo centro histórico
    Visita aos principais pontos turísticos do centro, incluindo museus e igrejas, seguido de almoço em restaurante típico.

    Repita essa estrutura para todos os dias, sempre adaptando para o idioma e perfil especificado.
    """)

    planner = Agent(
        name="Planner",
        role="Generates a draft itinerary based on user preferences and research results",
        model=OpenAIChat(id="gpt-4o", api_key=openai_api_key),
        description=dedent(
            f"""\
            You are a senior travel planner. Given a travel destination, number of days, travel profile, preferred language, and research results,
            your goal is to generate a draft itinerary that meets the user's needs and preferences. Use the provided format and rules.
            """
        ),
        instructions=[
            planner_prompt_instructions
        ],
        add_datetime_to_instructions=True,
    )

    if st.button("Gerar Itinerário"):
        if not destination:
            st.warning("Por favor, informe o destino da viagem.")
        else:
            with st.spinner("Pesquisando o destino..."):
                research_results = researcher.run(
                    f"Research for a {profile} ({profile_human}) {num_days}-day trip to {destination}. All results should be in {language} ({language_human}).",
                    stream=False
                )
                st.success("✓ Pesquisa concluída!")

            with st.spinner("Criando seu roteiro personalizado..."):
                planner_prompt = (
                    f"Destino: {destination}\n"
                    f"Duração: {num_days} dias\n"
                    f"Perfil de viagem: {profile} ({profile_human})\n"
                    f"Idioma do roteiro: {language} ({language_human})\n"
                    f"Resultados da pesquisa: {research_results.content}\n\n"
                    f"Por favor, siga exatamente as instruções fornecidas para criar um roteiro detalhado e organizado (sem imagens, apenas títulos e descrições)."
                )
                response = planner.run(planner_prompt, stream=False)
                st.success("✓ Roteiro criado!")

                # Parsing robusto do roteiro
                # Busca todos os blocos "Dia X: Título"
                dias = re.split(r'\bDia (\d+):\s*([^\n]+)', response.content, flags=re.IGNORECASE)

                if len(dias) > 2:
                    for i in range(1, len(dias), 3):
                        dia_num = dias[i]
                        dia_titulo = dias[i+1].strip()
                        dia_descricao = dias[i+2].strip()
                        # Busca imagem real no Unsplash usando o título do dia
                        img_url = buscar_imagem_unsplash(dia_titulo, unsplash_access_key)

                        # Layout: imagem pequena ao lado do texto
                        col1, col2 = st.columns([1, 5])
                        with col1:
                            if img_url:
                                st.image(img_url, width=110)
                        with col2:
                            st.markdown(f"**Dia {dia_num}: {dia_titulo}**")
                            st.write(dia_descricao)
                else:
                    st.write(response.content)