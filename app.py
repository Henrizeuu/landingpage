import streamlit as st
import os
import requests
import glob
import re
import shutil
import random
import time
import logging
import urllib.parse
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

def gerar_blueprint_estrategico(empresa: str, nicho: str, contexto_texto: str, imagens: list, menu: str, estrutura: str) -> str:
    """Executa o Mega Prompt I: O Arquiteto Estratégico, utilizando Chain of Thought."""
    adicionar_log("Iniciando processamento do Arquiteto (Mega Prompt I)...")
    
    prompt = f"""
<system_persona>Atue como o Arquiteto Principal de Interfaces (UX/UI) e Especialista em Conversão Comercial do sistema Epiverso. A sua competência central é projetar páginas institucionais de alto valor que respeitem PROFUNDAMENTE a identidade visual real do cliente.</system_persona>

<core_directives>
1. ESTRATÉGIA DE CONVERSÃO: O cliente atua no nicho de **{nicho}**. Redija textos diretos e persuasivos focados nas dores, objeções e jargões deste mercado. O tom deve transmitir máxima autoridade. A página é INSTITUCIONAL, não uma landing page agressiva.
2. ANÁLISE VISUAL OBRIGATÓRIA (CRÍTICO): Você DEVE observar as imagens anexadas do portfólio do cliente antes de definir cores. 
   - Se as fotos mostrarem ambientes claros, É EXPRESSAMENTE PROIBIDO usar fundo escuro. Você DEVE usar um tema claro (Light Mode) que reflita o trabalho do cliente.
3. SELEÇÃO DE COMPONENTES: O mapeamento entre a <estrutura_exigida> e o <catalogo_componentes> deve ser exato.
4. MUTAÇÃO DINÂMICA DE LAYOUT: Para garantir que a página institucional seja única, você DEVE sugerir alterações estruturais (mutações) rigorosas para pelo menos dois blocos do catálogo. Por exemplo, instruir a transformação de uma lista padrão num grid de 3 colunas, ou alterar a disposição da imagem de perfil.
5. FOTO DE PERFIL: A imagem "foto_perfil.webp" deve ser usada EXCLUSIVAMENTE em uma tag <img> de apresentação no Topo/Hero. É ESTRITAMENTE PROIBIDO usá-la como imagem de fundo (background-image).
</core_directives>

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
Gere o blueprint definindo as cores estritas e listando cada bloco da estrutura. Para os blocos escolhidos, passe instruções de mutação de CSS/Layout para o Engenheiro.
</task>

<output_format>
# 🎨 IDENTIDADE VISUAL E TOKENS DA PÁGINA
* **Tema**:
* **Paleta de Cores Gerada**:
  * `--bg-page`: [Hexadecimal exato]
  * `--text-main`: [Hexadecimal exato]
  * `--accent-color`: [Hexadecimal vibrante extraído das fotos ou da marca]
* **Tipografia (Google Fonts)**: [Duas fontes perfeitamente alinhadas]

# 🏗️ BLUEPRINT DA PÁGINA INSTITUCIONAL

## 1. [Nome da Secção conforme Estrutura Exigida]
* **Blocos Escolhidos**: [ID: XXX] - [Nome do bloco]
* **Instruções de Adaptação (Design & MUTAÇÃO)**: [Diretriz exata para o engenheiro. Ex: "MUTAÇÃO: Usar Tailwind para converter as divs filhas num flexbox row gap-8", "Manter fundo bege claro"]
* **Copywriting**:
  * **Kicker/Eyebrow**: "..."
  * **Título Principal**: "..."
  * **Subtítulo/Texto de Apoio**: "..."
  * **Call to Action (Botão)**: "..."
</output_format>
"""
    # Temperatura aumentada para gerar layouts mais criativos e únicos
    config = types.GenerateContentConfig(temperature=0.6)
    conteudo_envio = [prompt] + imagens
    
    try:
        resposta = client_gemini.models.generate_content(
            model='gemini-3.5-flash',
            contents=conteudo_envio,
            config=config
        )
        if not resposta or not hasattr(resposta, 'text') or not resposta.text:
            raise ValueError("O Google Gemini não retornou nenhum texto.")
            
        adicionar_log("Blueprint Arquitetural gerado com sucesso.")
        return str(resposta.text)
    except Exception as e:
        adicionar_log(f"Erro Crítico no Gemini (Arquiteto): {str(e)}")
        raise e

def coletar_codigos_fontes(blueprint_text: str) -> str:
    """Busca no diretório local os arquivos TXT correspondentes aos IDs mapeados no Blueprint."""
    if not blueprint_text or not isinstance(blueprint_text, str):
        adicionar_log("Erro: O blueprint recebido para coleta de IDs está vazio ou inválido.")
        return ""
        
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

def gerar_codigo_engenheiro(blueprint_text: str, codigos_base: str, empresa: str, cidade: str = "") -> str:
    """Executa o Mega Prompt II: Engenheiro de Síntese, gerando o HTML final exaustivo."""
    if not blueprint_text or not codigos_base:
        raise ValueError("O Engenheiro não recebeu o blueprint ou os códigos base necessários para trabalhar.")
        
    adicionar_log("Iniciando compilação do Engenheiro (Mega Prompt II)...")
    empresa_mapa = urllib.parse.quote_plus(f"{empresa} {cidade}".strip())
    
    prompt = f"""
<system_persona>Atue como um Engenheiro Frontend Especialista e Arquiteto de Sistemas de Interface da Epiverso. Seu domínio é manipulação de DOM, Tailwind CSS e GSAP para criar páginas institucionais cinematográficas estáticas de alto impacto para a área contábil e corporativa.</system_persona>

<core_constraints>
1. STATIC HERO CINEMATOGRÁFICO: O topo da página DEVE ser um "Static Hero". É ESTRITAMENTE PROIBIDO usar a imagem `foto_perfil.webp` como imagem de fundo (background-image), pois isso causará distorção extrema. Para o fundo da seção Hero, use apenas cores sólidas ou um gradiente elegante via Tailwind CSS. A imagem `foto_perfil.webp` deve ser usada APENAS em uma tag `<img>` dentro da estrutura lateral do Hero.
2. SISTEMA DE LEGIBILIDADE: Garanta contraste absoluto (no mínimo 3.5:1) entre o fundo da seção Hero e o texto por cima.
3. ANIMAÇÕES GSAP (PROIBIDO EIXO Y): Use GSAP com ScrollTrigger. É ESTRITAMENTE PROIBIDO qualquer movimento de subida (banido o uso de `y`, `translateY`). Use APENAS variações de `opacity`, `scale` e entrada lateral (`x`). 
4. ESTRUTURA INSTITUCIONAL: A página não é uma landing page agressiva; é uma página institucional desenhada para conquistar clientes. Use Tailwind CSS via CDN para aplicar as mutações exigidas pelo Arquiteto.
5. ASSINATURA E MAPA: Inclua a assinatura da Epiverso no footer e o iframe do Google Maps para "{empresa_mapa}" imediatamente antes do rodapé.
6. FALLBACK: Todas as tags `<img>` devem ter `onerror="this.onerror=null; this.src='https://placehold.co/800x800/dedede/333?text=Imagem+Indisponivel'"`.
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
Compile a página completa em um único arquivo HTML, integrando Tailwind CSS, o Static Hero e as animações GSAP (restritas a eixo X, escala e opacidade).
</task>

<output_format>
```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Página Institucional - {empresa}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
    <style>
        /* CSS adicional aqui */
    </style>
</head>
<body>
    <!-- HTML EXAUSTIVO AQUI -->
    <script>
        gsap.registerPlugin(ScrollTrigger);
        /* Lógica GSAP blindada contra eixo Y aqui */
    </script>
</body>
</html>
```
</output_format>
"""
    config = types.GenerateContentConfig(temperature=0.0)

    try:
        resposta = client_gemini.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=config
        )
        if not resposta or not hasattr(resposta, 'text') or not resposta.text:
            raise ValueError("O Engenheiro (Gemini) retornou uma resposta em branco.")
            
        adicionar_log("Código fonte compilado com sucesso pelo Engenheiro.")
        return str(resposta.text)
    except Exception as e:
        adicionar_log(f"Erro Crítico no Gemini (Engenheiro): {str(e)}")
        raise e

def auditar_codigo_final(codigo_html: str, empresa: str, nicho: str) -> str:
    """Executa o Mega Prompt III: Auditor de Qualidade para lapidação final do HTML."""
    adicionar_log("Iniciando auditoria de qualidade (Mega Prompt III)...")
    empresa_mapa = urllib.parse.quote_plus(empresa)

    prompt = f"""
<system_persona>Atue como um Auditor Sênior de Qualidade (QA) e Especialista em UX/UI da Epiverso. Sua missão é inspecionar, corrigir e lapidar o código HTML/CSS/JS gerado pelo Engenheiro para garantir que seja uma verdadeira Página Institucional de altíssimo padrão, sem bugs e pronta para produção.</system_persona>

<core_directives>
1. REVISÃO ESTRUTURAL (ANTI-QUEBRA): Verifique o fechamento de TODAS as tags HTML. Garanta que não existam classes do Tailwind conflitantes ou elementos que causem transbordamento lateral na tela (overflow-x).
2. GUARDIÃO DA PÁGINA INSTITUCIONAL: Verifique o copy. Garanta que o tom de voz transmite máxima autoridade e confiança corporativa focada em adquirir clientes para o nicho de {nicho}. Remova qualquer jargão barato de "landing page de vendas" agressiva e substitua por postura institucional.
3. REFINAMENTO DE ANIMAÇÃO GSAP (CRÍTICO): Inspecione a tag `<script>`. VOCÊ DEVE REMOVER qualquer animação que faça os elementos "subirem" na tela no eixo Y (ex: `y: 20`, `translateY`). Apenas permita transições suaves de opacidade (`opacity`), escala (`scale`) ou entrada horizontal.
4. INTEGRIDADE DOS REQUISITOS OBRIGATÓRIOS: 
   - Confirme se o mapa do Google está renderizado usando a URL exata com `output=embed` antes do footer.
   - Verifique se a assinatura da agência `<p>Desenvolvido por <a href="https://epiverso.com"...` está intacta no rodapé.
5. PRESERVAÇÃO DE ATIVOS: Garanta que todas as imagens mantiveram a tag de segurança `onerror` para carregar placeholders caso a imagem local `.webp` falhe.
</core_directives>

<context>
<codigo_bruto_engenheiro>
{codigo_html}
</codigo_bruto_engenheiro>
</context>

<task>
Inspecione o <codigo_bruto_engenheiro>, aplique as correções necessárias silenciosamente e retorne APENAS o código HTML final e impecável.
</task>

<output_format>
```html
<!DOCTYPE html>
<!-- ESCREVA O CÓDIGO HTML COMPLETO E ABSOLUTAMENTE NADA MAIS. NÃO CORTE NENHUMA LINHA. -->
```
</output_format>
"""
# Temperatura baixa (0.1) para garantir precisão cirúrgica na correção de código

    config = types.GenerateContentConfig(temperature=0.1)
    
    try:
        resposta = client_gemini.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=config
        )
        if not resposta or not hasattr(resposta, 'text') or not resposta.text:
            raise ValueError("O Auditor (Gemini) retornou uma resposta em branco.")
            
        adicionar_log("Código final auditado e polido com sucesso pelo QA.")
        return str(resposta.text)
    except Exception as e:
        adicionar_log(f"Erro Crítico no Gemini (Arquiteto): {str(e)}")
        raise e


# =====================================================================
# 7. INTERFACE PRINCIPAL STREAMLIT
# =====================================================================
if not client_apify or not client_gemini:
    st.error("🚨 O sistema está inoperante devido à falta de credenciais nas configurações de Secrets do Streamlit.")
    st.stop()

with st.sidebar:
    st.header("⚙️ Painel de Controle Epiverso")
    st.markdown("Monitoramento em tempo real da orquestração de IA.")
    st.markdown("---")
    st.subheader("Console de Logs")
    
    log_container = st.empty()
    if st.session_state.logs_execucao:
        log_text = "\n".join(st.session_state.logs_execucao[-10:])
        log_container.code(log_text, language="bash")
    else:
        log_container.info("Aguardando inicialização do pipeline...")

st.markdown("### 1. Parâmetros do Cliente High-Ticket")
col1, col2, col3, col4 = st.columns(4)
with col1:
    empresa_input = st.text_input("📍 Nome do Negócio", placeholder="Ex: Escritório Alpha")
with col2:
    cidade_input = st.text_input("📍 Cidade/Endereço", placeholder="Ex: Santa Cruz do Sul")
with col3:
    insta_input = st.text_input("📸 Perfil do Instagram (Sem @)", placeholder="Ex: alphacontabilidade")
with col4:
    nicho_input = st.text_input("🎯 Nicho de Mercado", value="Contabilidade", placeholder="Ex: Contabilidade, Advocacia")

st.markdown("---")

if st.button("🚀 INICIAR PIPELINE DE ARQUITETURA", use_container_width=True):
    if not empresa_input or not insta_input:
        st.warning("⚠️ Preencha os campos obrigatórios.")
    else:
        st.session_state.processo_concluido = False
        st.session_state.logs_execucao = []
        pasta_alvo = os.path.join(DIR_DADOS, empresa_input.replace("/", "-").replace(" ", "_"))
        os.makedirs(pasta_alvo, exist_ok=True)
        progresso = st.progress(0)
        status_text = st.empty()

        try:
            status_text.markdown("#### ⏳ Etapa 1/5: Minerando dados brutos e provas sociais...")
            extrair_google_maps(empresa_input, pasta_alvo)
            progresso.progress(15)
            extrair_instagram(insta_input, pasta_alvo)
            progresso.progress(30)
            
            status_text.markdown("#### ⏳ Etapa 2/5: Preparando matrizes de contexto...")
            menu_texto, estrutura_texto = ler_arquivos_base()
            contexto_cli, imagens_cli = compilar_contexto_cliente(pasta_alvo)
            progresso.progress(45)
            
            status_text.markdown("#### ⏳ Etapa 3/5: O Arquiteto está analisando a presença digital...")
            blueprint = gerar_blueprint_estrategico(
                empresa_input, nicho_input, contexto_cli, imagens_cli, menu_texto, estrutura_texto
            )
            
            if not blueprint:
                raise Exception("O pipeline falhou pois a IA Arquiteto gerou um documento vazio.")
                
            st.session_state.blueprint_gerado = blueprint
            progresso.progress(70)
            
            status_text.markdown("#### ⏳ Etapa 4/5: O Engenheiro Sênior está compilando o código HTML bruto...")
            codigos_fragmentados = coletar_codigos_fontes(blueprint)
            codigo_bruto = gerar_codigo_engenheiro(blueprint, codigos_fragmentados, empresa_input, cidade_input)
            
            if not codigo_bruto:
                raise Exception("O pipeline falhou pois a IA Engenheiro gerou um código vazio.")
                
            progresso.progress(85)

            status_text.markdown("#### ⏳ Etapa 5/5: O Auditor de Qualidade está revisando todo o index e corrigindo falhas...")
            codigo_auditado = auditar_codigo_final(codigo_bruto, empresa_input, nicho_input)
            
            if not codigo_auditado:
                raise Exception("O pipeline falhou pois a IA Auditora gerou um código vazio.")

            st.session_state.codigo_gerado = codigo_auditado
            progresso.progress(95)
            
            status_text.markdown("#### ⏳ Finalizando e empacotando artefatos para a VPS...")
            pasta_build = os.path.join(DIR_BUILD, empresa_input.replace(" ", "_"))
            os.makedirs(pasta_build, exist_ok=True)
            
            match = re.search(r'```html(.*?)```', str(codigo_auditado), re.DOTALL | re.IGNORECASE)
            codigo_limpo = match.group(1).strip() if match else str(codigo_auditado).replace('```html', '').replace('```', '').strip()

            with open(os.path.join(pasta_build, "index.html"), "w", encoding="utf-8") as f:
                f.write(codigo_limpo)
                
            for img_webp in glob.glob(os.path.join(pasta_alvo, "*.webp")):
                shutil.copy(img_webp, pasta_build)
                
            caminho_zip = os.path.join(DIR_BUILD, f"PaginaInstitucional_{empresa_input.replace(' ', '_')}")
            zip_directory(pasta_build, caminho_zip)
            st.session_state.caminho_zip = f"{caminho_zip}.zip"
            st.session_state.processo_concluido = True
            progresso.progress(100)
            status_text.empty()
            st.balloons()
            
        except Exception as e:
            st.error(f"🚨 Falha Crítica no Fluxo: {str(e)}")
            adicionar_log(f"ERRO FATAL REPORTADO: {str(e)}")

# =====================================================================
# 8. EXIBIÇÃO DE RESULTADOS
# =====================================================================
if st.session_state.processo_concluido:
    st.markdown("---")
    st.markdown("### 🏆 Orquestração Finalizada com Sucesso")
    aba1, aba2, aba3 = st.tabs(["📦 Download do Pacote", "📐 Blueprint Arquitetural", "💻 Inspecionar Código Fonte"])

    with aba1:
        st.info("Página estruturada e cores alinhadas com o portfólio visual do cliente.")
        with open(st.session_state.caminho_zip, "rb") as fp:
            st.download_button(
                label="⬇️ BAIXAR ARQUIVO .ZIP COMPLETO",
                data=fp,
                file_name=os.path.basename(st.session_state.caminho_zip),
                mime="application/zip",
                use_container_width=True
            )
            
    with aba2:
        st.markdown(st.session_state.blueprint_gerado)
        
    with aba3:
        with st.expander("Expandir para visualizar o código HTML"):
            st.code(st.session_state.codigo_gerado, language="html")
