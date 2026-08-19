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

DIR_DADOS = "dados_empresas"
DIR_BUILD = "build_epiverso"

for directory in [DIR_DADOS, DIR_BUILD]:
    os.makedirs(directory, exist_ok=True)

# =====================================================================
# 2. INFRAESTRUTURA UI PREMIUM (EPIVERSO)
# =====================================================================
st.set_page_config(
    page_title="Epiverso | Architect AI Engine", 
    page_icon="🏛️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Tema Dark Neo-Corporativo Epiverso */
        .stApp {
            background-color: #080808;
            color: #e5e7eb;
            font-family: 'Inter', sans-serif;
        }
        
        /* Inputs e Formulários */
        .stTextInput>div>div>input, .stSelectbox>div>div>select {
            background-color: #111827 !important;
            color: #ffffff !important;
            border: 1px solid #374151 !important;
            border-radius: 6px;
            padding: 14px;
            font-size: 14px;
        }
        .stTextInput>div>div>input:focus {
            border-color: #b2fe02 !important;
            box-shadow: 0 0 0 1px rgba(178, 254, 2, 0.3) !important;
        }
        
        /* Botões de Ação Principal */
        .stButton>button {
            background-color: #b2fe02 !important;
            color: #0a0a0a !important;
            border-radius: 4px !important;
            padding: 1rem 3rem !important;
            font-weight: 900 !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            border: none !important;
            transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1) !important;
            box-shadow: 0 4px 15px rgba(178, 254, 2, 0.1) !important;
            width: 100%;
        }
        .stButton>button:hover {
            transform: translateY(-4px) !important;
            box-shadow: 0 15px 35px rgba(178, 254, 2, 0.4) !important;
            background-color: #c7ff4d !important;
        }
        
        /* Paineis de Status */
        .streamlit-expanderHeader {
            background-color: #111827 !important;
            border-radius: 4px;
            color: #b2fe02 !important;
            font-weight: bold;
        }
        div[data-testid="stStatusWidget"] {
            background-color: #111827 !important;
            border: 1px solid #374151;
            border-left: 4px solid #b2fe02;
            border-radius: 4px;
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
    adicionar_log(f"Iniciando compactação do diretório: {folder_path}")
    shutil.make_archive(zip_path, 'zip', folder_path)
    adicionar_log(f"Compactação concluída: {zip_path}.zip")

def extrair_google_maps(empresa: str, pasta_destino: str, max_reviews: int = 10) -> bool:
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
        
        dataset_id = run.get("defaultDatasetId") or getattr(run, "default_dataset_id", None)
        
        if dataset_id:
            for place in client_apify.dataset(dataset_id).iterate_items():
                avaliacoes = []
                for r in place.get("reviews", [])[:max_reviews]:
                    texto = r.get('text', '')
                    if texto:
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
    adicionar_log(f"Iniciando raspagem do Instagram para o perfil: @{usuario}")
    sucesso = False
    try:
        run_profile = client_apify.actor("apify/instagram-scraper").call(
            run_input={"resultsType": "details", "directUrls": [f"https://www.instagram.com/{usuario}/"]}
        )
        dataset_profile_id = run_profile.get("defaultDatasetId") or getattr(run_profile, "default_dataset_id", None)
        
        if dataset_profile_id:
            for item in client_apify.dataset(dataset_profile_id).iterate_items():
                bio = item.get("biography", "Sem biografia fornecida.")
                with open(os.path.join(pasta_destino, "insta_bio.txt"), "w", encoding="utf-8") as f:
                    f.write(f"--- BIO DO INSTAGRAM (@{usuario}) ---\n{bio}")
                adicionar_log("Sucesso: Biografia do Instagram extraída.")
                break

        adicionar_log(f"Buscando as últimas {max_posts} publicações...")
        run_posts = client_apify.actor("apify/instagram-scraper").call(
            run_input={"resultsType": "posts", "directUrls": [f"https://www.instagram.com/{usuario}/"], "resultsLimit": max_posts}
        )
        dataset_posts_id = run_posts.get("defaultDatasetId") or getattr(run_posts, "default_dataset_id", None)
        
        if dataset_posts_id:
            contador_img = 1
            for item in client_apify.dataset(dataset_posts_id).iterate_items():
                if contador_img > max_posts: break
                
                legenda = item.get("caption", "Sem legenda.")
                with open(os.path.join(pasta_destino, f"insta_post_{contador_img}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"[POST {contador_img}]\n{legenda}")
                    
                urls = item.get("carouselImages") or (item.get("images") if item.get("images") else [item.get("displayUrl")])
                if urls:
                    for url in urls[:1]:
                        try:
                            resp = requests.get(url, timeout=15)
                            if resp.status_code == 200:
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
    try:
        if not os.path.exists("menu (1).txt"):
            raise FileNotFoundError("Arquivo vital não encontrado: menu (1).txt")
        if not os.path.exists("estrutura (1).txt"):
            raise FileNotFoundError("Arquivo vital não encontrado: estrutura (1).txt")
            
        with open("menu (1).txt", "r", encoding="utf-8") as f:
            menu = f.read()
        with open("estrutura (1).txt", "r", encoding="utf-8") as f:
            estrutura = f.read()
            
        return menu, estrutura
    except Exception as e:
        adicionar_log(f"Erro de I/O: {str(e)}")
        raise e

def compilar_contexto_cliente(pasta_cliente: str) -> tuple[str, list]:
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
    adicionar_log("Iniciando processamento do Arquiteto (Mega Prompt I)...")
    
    # MEGA PROMPT I: Estruturado rigorosamente com aspas simples triplas para evitar colisões
    prompt = f'''
<system_persona>Atue como o Arquiteto Principal de Interfaces (UX/UI) e Especialista em Conversão Comercial do sistema Epiverso. A sua competência central é projetar páginas institucionais de alto valor para prestadores de serviços, cruzando a psicologia do consumidor com a estética minimalista e luxuosa.</system_persona>

<core_directives>
1. ESTRATÉGIA DE CONVERSÃO: Redija textos diretos, persuasivos e baseados na resolução de problemas extraídos dos <dados_cliente>. É imperativo evitar formulações robóticas e genéricas. O tom deve transmitir autoridade e focar na captação de clientes corporativos ou de alto ticket.
2. ADAPTAÇÃO TEMÁTICA: A estética final exige obrigatoriamente a abordagem: **{estetica}**. Você selecionará componentes que nativamente possam ser escuros, devendo planear e documentar as ordens exatas de inversão de propriedades de cor (fundos, textos, sombras) para o engenheiro subsequente.
3. SELEÇÃO DE COMPONENTES: O mapeamento entre a <estrutura_exigida> e o <catalogo_componentes> deve ser exato e cirúrgico.
4. LEITURA VISUAL: Analise as imagens enviadas e defina uma `--accent-color` (Cor de Destaque) no formato hexadecimal baseando-se na paleta dominante da identidade do cliente.
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
Antes de materializar o projeto, execute uma decomposição lógica do seu planeamento dentro da etiqueta <analise_estrategica>, justificando as suas escolhas passo a passo. Após a análise, forneça o projeto final seguindo escrupulosamente a formatação exigida em Markdown.

<analise_estrategica>
1. Diagnóstico do Público: [Avaliação das dores e necessidades baseadas no Maps/Instagram].
2. Lógica Cromática: [Justificação para as cores hexadecimais escolhidas baseadas nas imagens e estética solicitada].
3. Mapeamento Lógico: [Associação de cada secção da estrutura ao ID específico do catálogo].
</analise_estrategica>

# 🎨 IDENTIDADE VISUAL E TOKENS DA PÁGINA
* **Tema**: {estetica}
* **Paleta de Cores Gerada**:
  * `--bg-page`: [Hexadecimal muito claro]
  * `--text-main`: [Hexadecimal escuro para contraste]
  * `--accent-color`: [Hexadecimal vibrante extraído das imagens]
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
'''
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
    adicionar_log("Iniciando compilação do Engenheiro (Mega Prompt II)...")
    
    # MEGA PROMPT II: Estruturado rigorosamente com aspas simples triplas para evitar colisões de sintaxe
    prompt = f'''
<system_persona>Atue como um Engenheiro Frontend Especialista e Arquiteto de Sistemas de Interface da Epiverso. Possui domínio absoluto sobre manipulação avançada de Document Object Model (DOM), propriedades CSS variáveis (Custom Properties) e arquitetura de animações utilizando Vanilla JavaScript e bibliotecas GSAP.</system_persona>

<core_constraints>
[IMPORTANTE]: O seu objetivo primário é a COMPILAÇÃO e MONTAGEM EXAUSTIVA. Nenhuma linha de código deve ser omitida.
1. PROIBIDO ECONOMIZAR CÓDIGO: Escreva o script de fora a fora. Não abrevie, não crie módulos incompletos e NUNCA use placeholders como "adicione o resto aqui". Eu exijo a página 100% pronta para ir ao ar.
2. INTOCABILIDADE ESTRUTURAL: É absolutamente proibido alterar a hierarquia das etiquetas HTML, eliminar classes existentes ou reescrever a arquitetura das divisórias (divs) fornecidas nos códigos fonte.
3. BANIMENTO DE FRAMEWORKS EXTERNOS: Todo o código deve operar nativamente (Plain HTML, CSS, JS). Proibido Tailwind CSS ou React.
4. CONVERSÃO DE TEMAS (DARK PARA LIGHT PREMIUM): A maioria dos blocos fornecidos tem génese no modo escuro. O seu dever é aplicar engenharia inversa nas variáveis cromáticas (inverter de escuro para claro).
5. ASSINATURA OBRIGATÓRIA DA AGÊNCIA: No Footer da página, inclua EXATAMENTE o seguinte HTML: 
   <p>Desenvolvido por <a href="https://epiverso.com" target="_blank" style="color: var(--accent-color); font-weight: bold; text-decoration: none;">EPIVERSO</a></p>
6. GALERIA DE FOTOS (WEBP): Quando inserir imagens do portfólio no HTML, utilize estritamente a nomenclatura sequencial: foto1.webp, foto2.webp, foto3.webp...
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
1. Extraia a paleta de cores e tipografia do <projeto_arquitetonico> e converta-as num seletor :root unificado na tag style.
2. Inicie a montagem do ficheiro HTML, substituindo o conteúdo textual de placeholder e os caminhos de imagens pelas diretrizes exatas do projeto.
3. Agregue todos os fragmentos de CSS na tag style, garantindo a lógica de inversão de cor.
4. Centralize toda a lógica JavaScript na tag script no final do body.
</task>

<output_format>
Antes da geração final do código, planeie a fusão executando uma <verificacao_de_sintese>.
A sua resposta deve conter estritamente blocos de código formatados da seguinte forma:

<verificacao_de_sintese>
1. Validação de Conflitos: [Análise...]
2. Adaptação de Cores: [Análise...]
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
