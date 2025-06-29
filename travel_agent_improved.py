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
        response = requests.get(url, params=params, timeout=7)
        if response.status_code == 200:
            data = response.json()
            return data["urls"]["regular"]
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

    # PROMPT atualizado para garantir resumo e detalhe entre 3 e 5 linhas e orçamento total só ao final
    planner_prompt_instructions = dedent(f"""
    Você é um especialista em viagens, responsável por criar roteiros personalizados de alta qualidade para {profile_human} ({profile}) em {language_human}.
    Para cada dia do roteiro, crie:
    - Um título curto e objetivo para o dia.
    - Um resumo do dia, entre 3 e 5 linhas, descrevendo as principais atividades e experiências, de forma clara, envolvente e objetiva.
    - Um orçamento estimado para o dia (apenas o valor numérico, ex: 150).
    - Um detalhe histórico ou cultural sobre o local principal das atividades do dia, entre 3 e 5 linhas, interessante, relevante e que aprofunde o entendimento sobre o destino.

    Estruture cada dia exatamente assim (no idioma do usuário):

    Dia X: [Título do dia]
    Resumo: [Resumo do dia, entre 3 e 5 linhas.]
    Orçamento estimado: [valor, ex: 150]
    Detalhe histórico/cultural: [curiosidade ou fato, entre 3 e 5 linhas.]

    Regras:
    - O título deve ser uma frase curta (exemplo: 'Passeio pelo centro histórico', 'Aventura nas trilhas', 'Dia em família no parque aquático').
    - O resumo deve ter entre 3 e 5 linhas, ser prático, informativo e útil para o viajante, refletindo o perfil da viagem, as preferências do usuário e o idioma escolhido.
    - O orçamento deve ser sempre apenas o valor numérico do dia, sem símbolos, texto ou moeda.
    - O detalhe histórico/cultural deve ser interessante, relevante e conter entre 3 e 5 linhas.
    - O roteiro deve ser visualmente organizado e fácil de ler, com cada dia separado pelo cabeçalho “Dia X: [Título]”.

    Exemplo de resposta para um dia (em português):

    Dia 1: Passeio pelo centro histórico
    Resumo: Explore as ruas antigas do centro histórico, visitando museus e igrejas emblemáticas da cidade. Experimente um almoço típico em restaurante tradicional e aproveite o clima acolhedor das praças. Tire fotos em pontos turísticos famosos e aproveite para conhecer lojas de artesanato local. Finalize o dia com uma caminhada ao entardecer pelas alamedas arborizadas.
    Orçamento estimado: 180
    Detalhe histórico/cultural: O centro histórico da cidade reúne construções do século XIX e XX, testemunhando diferentes fases da urbanização local. A principal igreja foi palco de importantes acontecimentos políticos e sociais. Muitas ruas mantêm o calçamento original de pedra portuguesa. A região preserva traços da colonização europeia, visíveis na arquitetura e nos costumes. O artesanato local é reconhecido como patrimônio cultural, sendo transmitido por gerações.

    Repita essa estrutura para todos os dias, sempre adaptando para o idioma e perfil especificado.

    Ao final, some e mostre o orçamento total estimado para a viagem neste formato (em {language_human}):
    Orçamento total estimado: [valor total]
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
                    f"Por favor, siga exatamente as instruções fornecidas para criar um roteiro detalhado e organizado, incluindo orçamento diário, detalhe histórico/cultural (entre 3 e 5 linhas), resumo do dia (entre 3 e 5 linhas) e o orçamento total apenas ao final."
                )
                response = planner.run(planner_prompt, stream=False)
                st.success("✓ Roteiro criado!")

                content = response.content
                if isinstance(content, bytes):
                    content = content.decode("utf-8")

                # Parsing robusto do roteiro
                dias = re.split(r'\bDia (\d+):\s*([^\n]+)', content, flags=re.IGNORECASE)

                orcamento_total = 0.0
                orcamento_total_modelo = None

                if len(dias) > 2:
                    for i in range(1, len(dias)-1, 3):
                        try:
                            dia_num = dias[i]
                            dia_titulo = dias[i+1].strip()
                            dia_conteudo = dias[i+2].strip()

                            resumo_match = re.search(r'Resumo:\s*(.*)', dia_conteudo)
                            orcamento_match = re.search(r'Orçamento estimado:\s*([\d\.,]+)', dia_conteudo)
                            detalhe_match = re.search(r'Detalhe histórico/cultural:\s*(.*)', dia_conteudo, re.DOTALL)

                            dia_resumo = resumo_match.group(1).strip() if resumo_match else ""
                            dia_orcamento = orcamento_match.group(1).replace(',', '.').strip() if orcamento_match else "0"
                            try:
                                orcamento_float = float(dia_orcamento)
                            except Exception:
                                orcamento_float = 0.0
                            orcamento_total += orcamento_float
                            dia_detalhe = detalhe_match.group(1).strip() if detalhe_match else ""

                            # Busca imagem real no Unsplash usando o título do dia
                            img_url = buscar_imagem_unsplash(dia_titulo, unsplash_access_key)

                            col1, col2 = st.columns([2, 5])
                            with col1:
                                if img_url:
                                    st.image(img_url, width=280)
                            with col2:
                                st.markdown(f"**Dia {dia_num}: {dia_titulo}**")
                                st.write(dia_resumo)
                                st.markdown(f"**Orçamento estimado:** R$ {orcamento_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                if dia_detalhe:
                                    with st.expander("Detalhes históricos e culturais"):
                                        st.write(dia_detalhe)
                        except Exception as e:
                            st.warning(f"Não foi possível processar o dia {(i//3)+1}: {e}")

                    # Orçamento total do modelo (caso ele forneça)
                    orcamento_total_match = re.search(r'Orçamento total estimado:\s*([\d\.,]+)', content)
                    if orcamento_total_match:
                        try:
                            orcamento_total_modelo = float(orcamento_total_match.group(1).replace(',', '.'))
                        except Exception:
                            orcamento_total_modelo = None

                    st.markdown("---")
                    st.markdown(f"## Orçamento total estimado: R$ {orcamento_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    if orcamento_total_modelo is not None and abs(orcamento_total - orcamento_total_modelo) > 1:
                        st.info(f"Orçamento total do modelo: R$ {orcamento_total_modelo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                else:
                    st.write(content)