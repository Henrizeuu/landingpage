import streamlit as st
import os
import requests
import glob
import re
import shutil
import random
import time
import logging
from PIL import Image
from apify_client import ApifyClient
from google import genai
from google.genai import types

# =====================================================================
# 1. CONFIGURAÇÃO DE LOGS E AMBIENTE
# =====================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Diretórios do Sistema
DIR_DADOS = "dados_empresas"
DIR_BUILD = "build_epiverso"
ARQ_MENU = "menu.txt"
ARQ_ESTRUTURA = "estrutura.txt"

for directory in [DIR_DADOS, DIR_BUILD]:
    os.makedirs(directory, exist_ok=True)

# =====================================================================
# 2. INFRAESTRUTURA UI PREMIUM (EPIVERSO)
# =====================================================================
st.markdown("""
    <style>
        /* Tipografia de Alta Legibilidade */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        /* Ocultar poluição visual do Streamlit */
        #MainMenu {visibility: hidden;}
        header[data-testid="stHeader"] { background: transparent !important; }
        footer { visibility: hidden; }
        
        /* Fundo Geral - Tema Claro Clean e Premium */
        .stApp {
            background-color: #F8FAFC; /* Cinza gelo super claro */
            color: #1E293B; /* Texto grafite escuro */
            font-family: 'Inter', sans-serif;
        }
        
        /* Títulos com Visibilidade Total (Escuros) */
        h1, h2, h3, h4 {
            color: #0F172A !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }
        
        /* Sidebar Branca para separar do fundo */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0;
        }

        /* =========================================
           INPUTS E CAIXAS DE TEXTO
           ========================================= */
        .stTextInput input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
            font-size: 15px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        }
        .stTextInput input:focus {
            border-color: #2563EB !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        }

        /* =========================================
           CORREÇÃO DO SELECTBOX (MENU DE OPÇÕES)
           ========================================= */
        /* Caixa principal do Select */
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        }
        /* Texto selecionado */
        div[data-baseweb="select"] div[class*="singleValue"] {
            color: #0F172A !important;
        }
        /* Fundo do Menu Suspenso (A lista que abre) */
        div[data-baseweb="popover"] ul[role="listbox"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            padding: 4px !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
        }
        /* Itens da lista */
        div[data-baseweb="popover"] li {
            color: #334155 !important;
            font-size: 15px !important;
            border-radius: 4px !important;
        }
        /* Hover quando passa o mouse na opção */
        div[data-baseweb="popover"] li:hover {
            background-color: #F1F5F9 !important;
            color: #0F172A !important;
        }

        /* =========================================
           BOTÃO PRINCIPAL DE AÇÃO
           ========================================= */
        .stButton>button {
            background-color: #2563EB !important; /* Azul Corporativo Vibrante */
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 16px !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            width: 100%;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
        }
        .stButton>button:hover {
            background-color: #1D4ED8 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3) !important;
        }
        
        /* Paineis de Status, Alertas e Expansores */
        div[data-testid="stStatusWidget"], .streamlit-expanderHeader, div[data-testid="stAlert"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            color: #0F172A !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        }
        div[data-testid="stStatusWidget"] {
            border-left: 4px solid #2563EB !important;
        }
        
        /* Abas (Tabs) - Visibilidade Limpa */
        .stTabs [data-baseweb="tab-list"] {
            background-color: transparent;
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 6px !important;
            color: #64748B !important;
            padding: 12px 20px !important;
            height: auto !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            border-bottom: 2px solid #2563EB !important;
            font-weight: 700 !important;
        }

        /* Console de Logs - Clean */
        pre {
            background-color: #F1F5F9 !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            color: #334155 !important;
            font-family: monospace;
        }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 3. GESTÃO DE ESTADO (SESSION STATE)
# =====================================================================
if 'processo_concluido' not in st.session_state:
    st.session_state.processo_concluido = False
if 'logs_execucao' not in st.session_state:
    st.session_state.logs_execucao = []
if 'blueprint_gerado' not in st.session_state:
    st.session_state.blueprint_gerado = ""
if 'codigo_gerado' not in st.session_state:
    st.session_state.codigo_gerado = ""
if 'caminho_zip' not in st.session_state:
    st.session_state.caminho_zip = ""

def adicionar_log(mensagem):
    timestamp = time.strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {mensagem}"
    st.session_state.logs_execucao.append(log_msg)
    logger.info(mensagem)

# =====================================================================
# 4. CARREGAMENTO DE CREDENCIAIS
# =====================================================================
@st.cache_resource
def init_clients():
    try:
        apify_token = st.secrets.get("APIFY_TOKEN")
        gemini_key = st.secrets.get("GEMINI_API_KEY")
        
        if not apify_token or not gemini_key:
            raise KeyError("Chaves ausentes")
            
        apify = ApifyClient(apify_token)
        gemini = genai.Client(api_key=gemini_key)
        return apify, gemini
    except Exception as e:
        return None, None

client_apify, client_gemini = init_clients()

# =====================================================================
# 5. MÓDULOS DE WEB SCRAPING AVANÇADO
# =====================================================================
def zip_directory(folder_path, zip_path):
    """Compacta o diretório de build para download."""
    adicionar_log(f"Iniciando compactação do diretório: {folder_path}")
    shutil.make_archive(zip_path, 'zip', folder_path)
    adicionar_log(f"Compactação concluída: {zip_path}.zip")

def extrair_google_maps(empresa: str, pasta_destino: str, max_reviews: int = 10) -> bool:
    """Extrai avaliações do Google Maps via Apify para a seção de Provas de Confiança."""
    adicionar_log(f"Solicitando dados do Google Maps para: {empresa}")
    try:
        run = client_apify.actor("compass/crawler-google-places").call(run_input={
            "searchStringsArray": [empresa],
            "maxCrawledPlacesPerSearch": 1,
            "scrapePlaceDetailPage": True,
            "maxReviews": max_reviews,
            "reviewsSort": "highestRanking",
            "scrapeContacts": False
        })
        
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "defaultDatasetId", getattr(run, "default_dataset_id", None))
        
        if dataset_id:
            for place in client_apify.dataset(dataset_id).iterate_items():
                avaliacoes = []
                for r in place.get("reviews", [])[:max_reviews]:
                    texto = r.get('text', '')
                    if texto:
                        # Limpa quebras de linha que possam quebrar o prompt
                        texto_limpo = texto.replace('\n', ' ').replace('\r', '')
                        avaliacoes.append(f"[{r.get('stars', 5)}⭐] {r.get('name', 'Cliente')}: {texto_limpo}")
                
                if avaliacoes:
                    caminho_arquivo = os.path.join(pasta_destino, "maps_reviews.txt")
                    with open(caminho_arquivo, "w", encoding="utf-8") as f:
                        f.write(f"--- AVALIAÇÕES DE {empresa} ---\n")
                        f.write("\n".join(avaliacoes))
                    adicionar_log(f"Sucesso: {len(avaliacoes)} avaliações do Maps extraídas.")
                    return True
        adicionar_log("Aviso: Nenhuma avaliação encontrada no Google Maps.")
        return False
    except Exception as e:
        adicionar_log(f"Erro Crítico no Scraper do Maps: {str(e)}")
        return False

def extrair_instagram(usuario: str, pasta_destino: str, max_posts: int = 8) -> bool:
    """Extrai bio e portfólio visual (em .webp) do Instagram via Apify."""
    adicionar_log(f"Iniciando raspagem do Instagram para o perfil: @{usuario}")
    sucesso = False
    try:
        # Extração de Detalhes do Perfil (Bio)
        run_profile = client_apify.actor("apify/instagram-scraper").call(
            run_input={"resultsType": "details", "directUrls": [f"https://www.instagram.com/{usuario}/"]}
        )
        dataset_profile_id = run_profile.get("defaultDatasetId") if isinstance(run_profile, dict) else getattr(run_profile, "defaultDatasetId", getattr(run_profile, "default_dataset_id", None))
        
        if dataset_profile_id:
            for item in client_apify.dataset(dataset_profile_id).iterate_items():
                # 1. Salva a Bio
                bio = item.get("biography", "Sem biografia fornecida.")
                with open(os.path.join(pasta_destino, "insta_bio.txt"), "w", encoding="utf-8") as f:
                    f.write(f"--- BIO DO INSTAGRAM (@{usuario}) ---\n{bio}")
                adicionar_log("Sucesso: Biografia do Instagram extraída.")
                
                # 2. Salva a Foto de Perfil (Adaptado para .webp)
                perfil_url = item.get("profilePicUrlHD") or item.get("profilePicUrl")
                if perfil_url:
                    try:
                        resp = requests.get(perfil_url, timeout=15)
                        if resp.status_code == 200:
                            caminho_perfil = os.path.join(pasta_destino, "foto_perfil.webp")
                            with open(caminho_perfil, "wb") as img_f:
                                img_f.write(resp.content)
                            adicionar_log("Sucesso: Foto de perfil extraída.")
                    except Exception as img_err:
                        adicionar_log(f"Aviso: Falha ao baixar foto de perfil: {str(img_err)}")
                
                break

        # Extração de Mídias e Legendas
        adicionar_log(f"Buscando as últimas {max_posts} publicações...")
        run_posts = client_apify.actor("apify/instagram-scraper").call(
            run_input={"resultsType": "posts", "directUrls": [f"https://www.instagram.com/{usuario}/"], "resultsLimit": max_posts}
        )
        dataset_posts_id = run_posts.get("defaultDatasetId") if isinstance(run_posts, dict) else getattr(run_posts, "defaultDatasetId", getattr(run_posts, "default_dataset_id", None))
        
        if dataset_posts_id:
            contador_img = 1
            for item in client_apify.dataset(dataset_posts_id).iterate_items():
                if contador_img > max_posts: break
                
                legenda = item.get("caption", "Sem legenda.")
                with open(os.path.join(pasta_destino, f"insta_post_{contador_img}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"[POST {contador_img}]\n{legenda}")
                    
                urls = item.get("carouselImages") or (item.get("images") if item.get("images") else [item.get("displayUrl")])
                if urls:
                    for url in urls[:1]: # Pega a primeira imagem de alta qualidade
                        try:
                            resp = requests.get(url, timeout=15)
                            if resp.status_code == 200:
                                # Conversão forçada para .webp conforme regras do Epiverso
                                caminho_img = os.path.join(pasta_destino, f"foto{contador_img}.webp")
                                with open(caminho_img, "wb") as img_f:
                                    img_f.write(resp.content)
                                contador_img += 1
                                sucesso = True
                        except Exception as img_err:
                            adicionar_log(f"Falha ao baixar imagem do post {contador_img}: {str(img_err)}")
                            pass
            adicionar_log(f"Sucesso: {contador_img - 1} mídias extraídas e convertidas para .webp.")
        return sucesso
    except Exception as e:
        adicionar_log(f"Erro Crítico no Scraper do Instagram: {str(e)}")
        return False

# =====================================================================
# 6. FUNÇÕES DE ORQUESTRAÇÃO DE IA (MEGA PROMPTS)
# =====================================================================
def ler_arquivos_base():
    """Lê os arquivos de Menu e Estrutura necessários para o prompt."""
    try:
        if not os.path.exists(ARQ_MENU):
            raise FileNotFoundError(f"Arquivo vital não encontrado: {ARQ_MENU}")
        if not os.path.exists(ARQ_ESTRUTURA):
            raise FileNotFoundError(f"Arquivo vital não encontrado: {ARQ_ESTRUTURA}")
            
        with open(ARQ_MENU, "r", encoding="utf-8") as f:
            menu = f.read()
        with open(ARQ_ESTRUTURA, "r", encoding="utf-8") as f:
            estrutura = f.read()
            
        return menu, estrutura
    except Exception as e:
        adicionar_log(f"Erro de I/O: {str(e)}")
        raise e

def compilar_contexto_cliente(pasta_cliente: str) -> tuple[str, list]:
    """Agrupa todos os TXTs e WEBP extraídos na fase de scraping."""
    contexto_texto = ""
    for txt_file in glob.glob(os.path.join(pasta_cliente, "*.txt")):
        with open(txt_file, "r", encoding="utf-8") as f:
            contexto_texto += f"\n<documento origem='{os.path.basename(txt_file)}'>\n{f.read()}\n</documento>\n"
            
    imagens = []
    for img_file in glob.glob(os.path.join(pasta_cliente, "*.webp")):
        try:
            imagens.append(Image.open(img_file))
        except Exception as e:
            adicionar_log(f"Aviso: Não foi possível carregar imagem para a IA {img_file}: {str(e)}")
            
    return contexto_texto, imagens

def gerar_blueprint_estrategico(empresa: str, contexto_texto: str, imagens: list, menu: str, estrutura: str, estetica: str) -> str:
    """Executa o Mega Prompt I: O Arquiteto Estratégico, utilizando Chain of Thought."""
    adicionar_log("Iniciando processamento do Arquiteto (Mega Prompt I)...")
    
    # Aplicação exata da arquitetura de prompt do documento "Melhoria Mega Prompts Epiverso.docx"
    prompt = f"""
<system_persona>Atue como o Arquiteto Principal de Interfaces (UX/UI) e Especialista em Conversão Comercial do sistema Epiverso. A sua competência central é projetar páginas institucionais de alto valor para prestadores de serviços, cruzando a psicologia do consumidor com a estética minimalista e luxuosa.</system_persona>

<core_directives>
1. ESTRATÉGIA DE CONVERSÃO: Redija textos diretos, persuasivos e baseados na resolução de problemas extraídos dos <dados_cliente>. É imperativo evitar formulações robóticas e genéricas. O tom deve transmitir autoridade e focar na captação de clientes corporativos ou de alto ticket.
2. ADAPTAÇÃO TEMÁTICA: A estética final exige obrigatoriamente a abordagem: **{estetica}**. Você selecionará componentes que nativamente possam ser escuros, devendo planear e documentar as ordens exatas de inversão de propriedades de cor (fundos, textos, sombras) para o engenheiro subsequente.
3. SELEÇÃO DE COMPONENTES: O mapeamento entre a <estrutura_exigida> e o <catalogo_componentes> deve ser exato e cirúrgico.
</core_directives>

<constraints>
- FIDELIDADE AO CATÁLOGO: É obrigatória a utilização exclusiva de identificadores de componentes que constem textualmente no <catalogo_componentes>.
- COMPREENSÃO POR CONTRASTE: 
  [Ação Rejeitada]: Escolher [ID: 999] por inferir que seria útil, apesar de não existir na lista fornecida. 
  [Ação Aprovada]: Analisar a necessidade de mostrar "Benefícios", percorrer a lista, encontrar o [ID: 059] - Benefits e instruir a sua adaptação para o tema exigido.
</constraints>

<context>
  <estrutura_exigida>
  {estrutura}
  </estrutura_exigida>
  
  <dados_cliente>
  Nome do Cliente: {empresa}
  {contexto_texto}
  </dados_cliente>
  
  <catalogo_componentes>
  {menu}
  </catalogo_componentes>
</context>

<task>
Sintetize as informações do <context> para traçar o perfil do prestador de serviço. Percorra meticulosamente a <estrutura_exigida> passo a passo. Para cada bloco lógico exigido, selecione o identificador numérico perfeito correspondente no <catalogo_componentes>. Após a seleção, redija o conteúdo persuasivo (Copy) para preencher a estrutura do componente e estipule as diretrizes de adaptação cromática para assegurar a consistência do tema.
</task>

<output_format>
Antes de materializar o projeto, execute uma decomposição lógica do seu planeamento dentro da etiqueta <analise_estrategica>, justificando as suas escolhas. Após a análise, forneça o projeto final seguindo escrupulosamente a formatação exigida em Markdown.

<analise_estrategica>
1. Diagnóstico do Público: [Avaliação das dores e necessidades baseadas no Maps/Instagram].
2. Lógica Cromática: [Justificação para as cores hexadecimais escolhidas baseadas nas imagens e estética solicitada].
3. Mapeamento Lógico: [Associação de cada secção da estrutura ao ID específico do catálogo].
</analise_estrategica>

# 🎨 IDENTIDADE VISUAL E TOKENS DA PÁGINA
* **Tema**: {estetica}
* **Paleta de Cores Gerada**:
  * `--bg-page`: [Hexadecimal]
  * `--text-main`: [Hexadecimal]
  * `--accent-color`: [Hexadecimal vibrante associado à marca do cliente]
* **Tipografia (Google Fonts)**: [Duas fontes elegantes]

# 🏗️ BLUEPRINT DA PÁGINA (ESTRUTURA)

## 1. [Nome da Secção conforme Estrutura Exigida]
* **Blocos Escolhidos**: [ID: XXX] - [Nome literal do bloco no catálogo]
* **Instruções de Adaptação (Design)**: [Diretriz exata para converter o bloco, mencionando sombras, fundos e opacidades]
* **Copywriting**:
  * **Kicker/Eyebrow**: "..."
  * **Título Principal**: "..."
  * **Subtítulo/Texto de Apoio**: "..."
  * **Call to Action (Botão)**: "..."
  * **Elementos Adicionais**: "..."
</output_format>
"""
    # Conforme o documento, a temperatura do Arquiteto deve ser entre 0.35 e 0.40
    config = types.GenerateContentConfig(temperature=0.35)
    conteudo_envio = [prompt] + imagens
    
    resposta = client_gemini.models.generate_content(
        model='gemini-3.5-flash',
        contents=conteudo_envio,
        config=config
    )
    adicionar_log("Blueprint Arquitetural gerado com sucesso.")
    return resposta.text

def coletar_codigos_fontes(blueprint_text: str) -> str:
    """Busca no diretório local os arquivos TXT correspondentes aos IDs mapeados no Blueprint."""
    adicionar_log("Analisando IDs mapeados e coletando códigos-fonte...")
    ids_selecionados = list(set(re.findall(r'\[ID:\s*(\d+)\]', blueprint_text)))
    adicionar_log(f"IDs identificados pela IA: {ids_selecionados}")
    
    codigo_dos_blocos = ""
    arquivos_encontrados = 0
    for comp_id in ids_selecionados:
        arquivos = glob.glob(f"*{comp_id}*.txt")
        for arq in arquivos:
            with open(arq, "r", encoding="utf-8") as f:
                codigo_dos_blocos += f"\n\n<!-- === COMPONENTE FONTE [ID: {comp_id}] ({arq}) === -->\n"
                codigo_dos_blocos += f.read()
                arquivos_encontrados += 1
                
    adicionar_log(f"Total de fragmentos de código injetados: {arquivos_encontrados}")
    return codigo_dos_blocos

def gerar_codigo_engenheiro(blueprint_text: str, codigos_base: str) -> str:
    """Executa o Mega Prompt II: Engenheiro de Síntese, gerando o HTML final exaustivo."""
    adicionar_log("Iniciando compilação do Engenheiro (Mega Prompt II)...")
    
    # Aplicação exata da arquitetura de prompt do documento "Melhoria Mega Prompts Epiverso.docx"
    prompt = f"""
<system_persona>Atue como um Engenheiro Frontend Especialista e Arquiteto de Sistemas de Interface da Epiverso. Possui domínio absoluto sobre manipulação avançada de Document Object Model (DOM), propriedades CSS variáveis (Custom Properties) e arquitetura de animações utilizando Vanilla JavaScript e bibliotecas GSAP.</system_persona>

<core_constraints>
[IMPORTANTE]: O seu objetivo primário é a COMPILAÇÃO e MONTAGEM EXAUSTIVA. Nenhuma linha de código deve ser omitida.
1. PROIBIDO ECONOMIZAR CÓDIGO: Escreva o script de fora a fora. Não abrevie, não crie módulos incompletos e NUNCA use placeholders como "adicione o resto aqui" ou "<!-- Mais itens da lista -->". Eu exijo a página 100% pronta para ir ao ar no servidor VPS do cliente.
2. INTOCABILIDADE ESTRUTURAL: É absolutamente proibido alterar a hierarquia das etiquetas HTML, eliminar classes existentes ou reescrever a arquitetura das divisórias (`divs`) fornecidas nos códigos fonte. A geometria dos componentes já está perfeita. O seu dever é unicamente posicionar os blocos na ordem exigida, alterar propriedades CSS e preenchê-los com o texto providenciado.
3. BANIMENTO DE FRAMEWORKS EXTERNOS: Todo o código deve operar nativamente (Plain HTML, CSS, JS). A inclusão não autorizada de bibliotecas como Tailwind CSS, Bootstrap ou React resultará em falha crítica.
4. ASSINATURA OBRIGATÓRIA DA AGÊNCIA: No Footer da página, inclua EXATAMENTE o seguinte HTML para os direitos reservados: 
   `<p>Desenvolvido por <a href="https://epiverso.com" target="_blank" style="color: var(--accent-color); font-weight: bold; text-decoration: none;">EPIVERSO</a></p>`.
5. GALERIA DE FOTOS (WEBP): Quando inserir imagens do portfólio no HTML, utilize estritamente a nomenclatura sequencial: `foto1.webp`, `foto2.webp`, `foto3.webp`, etc.
</core_constraints>

<context>
  <projeto_arquitetonico>
  {blueprint_text}
  </projeto_arquitetonico>
  
  <componentes_fonte>
  {codigos_base}
  </componentes_fonte>
</context>

<task>
1. Extraia a paleta de cores e tipografia do <projeto_arquitetonico> e converta-as num seletor `:root` unificado no início da tag `<style>`.
2. Inicie a montagem do ficheiro HTML, substituindo estritamente o conteúdo textual de placeholder e os caminhos de imagens pelas diretrizes exatas do projeto.
3. Agregue todos os fragmentos de CSS na tag `<style>`, certificando-se de que a lógica de inversão de cor ou adaptação de tema (ditada pelo arquiteto) é rigorosamente aplicada às classes originais.
4. Centralize toda a lógica JavaScript na tag `<script>` no final do body, assegurando que os detetores de deslocamento (Intersection Observers e ScrollTriggers) ocorram após o carregamento completo do documento.
</task>

<output_format>
Antes da geração final do código, planeie a fusão executando uma <verificacao_de_sintese>, identificando possíveis conflitos na união dos blocos e garantindo que o plano de cores respeita o limite do tema exigido.
A sua resposta deve conter estritamente blocos de código formatados da seguinte forma:

<verificacao_de_sintese>
1. Validação de Conflitos de Z-Index/Sticky: [Análise...]
2. Adaptação de Cores e Glassmorphism: [Análise...]
3. Injeção da Assinatura Epiverso: [Confirmado]
</verificacao_de_sintese>

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Página Institucional</title>
    <style>
        /* CSS EXAUSTIVO AQUI */
    </style>
</head>
<body>
    <!-- HTML EXAUSTIVO AQUI COM A CÓPIA DO ARQUITETO -->
    <script>
        /* JS EXAUSTIVO AQUI */
    </script>
</body>
</html>
</output_format>
</output_format>
"""
    # 👇 Todas as linhas abaixo precisam estar indentadas para dentro da função!
    
    # Conforme o documento, a temperatura do Engenheiro deve ser 0.0 para evitar invenções no código.
    config = types.GenerateContentConfig(temperature=0.0)

    resposta = client_gemini.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=config
    )
    adicionar_log("Código fonte compilado com sucesso pelo Engenheiro.")
    
    return resposta.text
# =====================================================================
# 7. INTERFACE PRINCIPAL STREAMLIT
# =====================================================================
if not client_apify or not client_gemini:
    st.error("🚨 O sistema está inoperante devido à falta de credenciais nas configurações de Secrets do Streamlit.")
    st.stop()

# --- SIDEBAR: Configurações e Logs ---
with st.sidebar:
    st.header("⚙️ Painel de Controle Epiverso")
    st.markdown("Monitoramento em tempo real da orquestração de IA.")

    st.subheader("Roteamento Dinâmico de Design")
    # Prevenção sistêmica da convergência de design
    esteticas_disponiveis = [
        "Light Premium (Corporativo Claro, cantos quadrados)",
        "Dark Mode Brutalista (Fundo Negro, tipografia robusta)",
        "Minimalismo Japandi (Tons terrosos, limpo e quente)",
        "Neumórfico de Luxo (Sombras suaves, fundo bege claro)",
        "Glassmorphism Moderno (Fundos translúcidos e vibrantes)"
    ]
    estetica_selecionada = st.selectbox(
        "Forçar Padrão Estético (Opcional):", 
        ["Sorteio Automático (IA decide)"] + esteticas_disponiveis
    )

    st.markdown("---")
    st.subheader("Console de Logs")
    log_container = st.empty()
    if st.session_state.logs_execucao:
        log_text = "\n".join(st.session_state.logs_execucao[-10:]) # Mostra os últimos 10
        log_container.code(log_text, language="bash")
    else:
        log_container.info("Aguardando inicialização do pipeline...")

# --- ÁREA PRINCIPAL ---
st.markdown("### 1. Parâmetros do Cliente High-Ticket")
st.markdown("Insira os dados do alvo da prospecção. O sistema desenhará uma página institucional corporativa completa.")

col1, col2 = st.columns(2)
with col1:
    empresa_input = st.text_input("📍 Nome do Negócio (Google Maps)", placeholder="Ex: Escritório de Contabilidade Alpha")
with col2:
    insta_input = st.text_input("📸 Perfil do Instagram (Sem @)", placeholder="Ex: alphacontabilidade")

st.markdown("---")

if st.button("🚀 INICIAR PIPELINE DE ARQUITETURA", use_container_width=True):
    if not empresa_input or not insta_input:
        st.warning("⚠️ Preencha os dois campos obrigatórios acima.")
    else:
        # Reset de estados
        st.session_state.processo_concluido = False
        st.session_state.logs_execucao = []

        pasta_alvo = os.path.join(DIR_DADOS, empresa_input.replace("/", "-").replace(" ", "_"))
        os.makedirs(pasta_alvo, exist_ok=True)
        
        estetica_final = random.choice(esteticas_disponiveis) if estetica_selecionada == "Sorteio Automático (IA decide)" else estetica_selecionada
        
        # --- INÍCIO DA EXECUÇÃO VISUAL ---
        progresso = st.progress(0)
        status_text = st.empty()
        
        try:
            # Etapa 1: Scraping
            status_text.markdown("#### ⏳ Etapa 1/4: Minerando dados brutos e provas sociais...")
            extrair_google_maps(empresa_input, pasta_alvo)
            progresso.progress(15)
            extrair_instagram(insta_input, pasta_alvo)
            progresso.progress(30)
            
            # Etapa 2: Leitura de Contexto
            status_text.markdown("#### ⏳ Etapa 2/4: Preparando matrizes de contexto...")
            menu_texto, estrutura_texto = ler_arquivos_base()
            contexto_cli, imagens_cli = compilar_contexto_cliente(pasta_alvo)
            progresso.progress(45)
            
            # Etapa 3: Arquiteto (Blueprint)
            status_text.markdown("#### ⏳ Etapa 3/4: O Arquiteto está desenhando o Blueprint Estratégico (Chain-of-Thought)...")
            blueprint = gerar_blueprint_estrategico(
                empresa_input, contexto_cli, imagens_cli, menu_texto, estrutura_texto, estetica_final
            )
            st.session_state.blueprint_gerado = blueprint
            progresso.progress(70)
            
            # Etapa 4: Engenheiro (Código HTML)
            status_text.markdown("#### ⏳ Etapa 4/4: O Engenheiro Sênior está compilando o código-fonte massivo...")
            codigos_fragmentados = coletar_codigos_fontes(blueprint)
            
            if not codigos_fragmentados:
                adicionar_log("AVISO: Os IDs gerados pelo arquiteto não correspondem a arquivos .txt locais.")
                
            codigo_completo = gerar_codigo_engenheiro(blueprint, codigos_fragmentados)
            st.session_state.codigo_gerado = codigo_completo
            progresso.progress(95)
            
            # Fechamento e Zip
            status_text.markdown("#### ⏳ Finalizando e empacotando artefatos...")
            pasta_build = os.path.join(DIR_BUILD, empresa_input.replace(" ", "_"))
            os.makedirs(pasta_build, exist_ok=True)
            
            # Limpeza via Regex para capturar só o conteúdo HTML
            match = re.search(r'```html(.*?)```', codigo_completo, re.DOTALL | re.IGNORECASE)
            codigo_limpo = match.group(1).strip() if match else codigo_completo.replace('```html', '').replace('```', '').strip()
            
            with open(os.path.join(pasta_build, "index.html"), "w", encoding="utf-8") as f:
                f.write(codigo_limpo)
                
            # Move as imagens .webp
            for img_webp in glob.glob(os.path.join(pasta_alvo, "*.webp")):
                shutil.copy(img_webp, pasta_build)
                
            caminho_zip = os.path.join(DIR_BUILD, f"LandingPage_{empresa_input.replace(' ', '_')}")
            zip_directory(pasta_build, caminho_zip)
            
            st.session_state.caminho_zip = f"{caminho_zip}.zip"
            st.session_state.processo_concluido = True
            progresso.progress(100)
            status_text.empty()
            st.balloons()
            
        except Exception as e:
            st.error(f"🚨 Ocorreu um erro crítico no pipeline: {str(e)}")
            adicionar_log(f"ERRO FATAL: {str(e)}")

# =====================================================================
# 8. EXIBIÇÃO DE RESULTADOS (ABAS)
# =====================================================================
if st.session_state.processo_concluido:
    st.markdown("---")
    st.markdown("### 🏆 Orquestração Finalizada com Sucesso")

    # Aba 1: Download, Aba 2: Blueprint, Aba 3: Código Bruto
    aba1, aba2, aba3 = st.tabs(["📦 Download do Pacote", "📐 Blueprint Arquitetural", "💻 Inspecionar Código Fonte"])

    with aba1:
        st.info("A página institucional foi estruturada com sucesso, as provas sociais foram injetadas e as imagens foram convertidas para .webp conforme as regras do Epiverso.")
        with open(st.session_state.caminho_zip, "rb") as fp:
            st.download_button(
                label="⬇️ BAIXAR ARQUIVO .ZIP COMPLETO",
                data=fp,
                file_name=os.path.basename(st.session_state.caminho_zip),
                mime="application/zip",
                use_container_width=True
            )
            
    with aba2:
        st.markdown("O documento abaixo foi gerado pelo **Mega Prompt I**, utilizando o raciocínio Chain-of-Thought antes de selecionar os componentes de UI/UX e estruturar a copy.")
        st.markdown(st.session_state.blueprint_gerado)
        
    with aba3:
        st.markdown("Código gerado pelo **Mega Prompt II**. O Engenheiro Sênior compilou as variáveis CSS, injetou a Copy e estruturou o HTML.")
        with st.expander("Expandir para visualizar o código"):
            st.code(st.session_state.codigo_gerado, language="html")

# Mantive a explicação final que você escreveu como markdown extra (você pode deixá-la dentro de st.markdown se quiser exibi-la na tela, ou apenas comentá-la se for documentação interna)
