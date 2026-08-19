import streamlit as st
import os
import requests
import glob
import re
import shutil
import random
from PIL import Image
from apify_client import ApifyClient
from google import genai
from google.genai import types

# =====================================================================
# 1. INFRAESTRUTURA UI PREMIUM (EPIVERSO)
# =====================================================================
st.set_page_config(page_title="Epiverso | Architect AI Engine", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp {
            background-color: #0c0c0c;
            color: #d7e2ea;
        }
        .stTextInput>div>div>input {
            background-color: #141618 !important;
            color: #ffffff !important;
            border: 1px solid #2a2d30 !important;
            border-radius: 8px;
            padding: 12px;
        }
        .stButton>button {
            background-color: #b2fe02 !important;
            color: #000000 !important;
            border-radius: 999px !important;
            padding: 0.85rem 2.5rem !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            border: none !important;
            transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1) !important;
            box-shadow: 0 10px 30px rgba(178, 254, 2, 0.15) !important;
        }
        .stButton>button:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 15px 40px rgba(178, 254, 2, 0.3) !important;
        }
        .status-box {
            background-color: #111827;
            border-left: 4px solid #b2fe02;
            padding: 1rem;
            border-radius: 4px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ Epiverso Architect | Sintetizador Institucional")
st.markdown("Motor de inteligência artificial de grau corporativo para estruturação de páginas institucionais de alta conversão.")

# =====================================================================
# 2. CARREGAMENTO DE CREDENCIAIS (BLINDADO)
# =====================================================================
@st.cache_resource
def init_clients():
    try:
        apify = ApifyClient(st.secrets["APIFY_TOKEN"])
        gemini = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        return apify, gemini
    except KeyError:
        return None, None

client_apify, client_gemini = init_clients()

if not client_apify or not client_gemini:
    st.error("⚠️ ERRO: Chaves APIFY_TOKEN e GEMINI_API_KEY ausentes nos secrets.")
    st.stop()

# =====================================================================
# 3. FUNÇÕES CORE DE SCRAPING E DADOS
# =====================================================================
def zip_directory(folder_path, zip_path):
    shutil.make_archive(zip_path, 'zip', folder_path)

def extrair_google_maps(empresa, pasta):
    run = client_apify.actor("compass/crawler-google-places").call(run_input={
        "searchStringsArray": [empresa],
        "maxCrawledPlacesPerSearch": 1,
        "scrapePlaceDetailPage": True,
        "maxReviews": 8,
        "reviewsSort": "highestRanking"
    })
    dataset_id = run.get("defaultDatasetId") or getattr(run, "default_dataset_id", None)
    
    if dataset_id:
        for place in client_apify.dataset(dataset_id).iterate_items():
            avaliacoes = [f"[{r.get('stars', 5)}⭐] {r.get('name', 'Cliente')}: {r.get('text', '').replace(chr(10), ' ')}" 
                          for r in place.get("reviews", [])[:8] if r.get("text")]
            if avaliacoes:
                with open(os.path.join(pasta, "maps_reviews.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(avaliacoes))
            break

def extrair_instagram(usuario, pasta):
    run_profile = client_apify.actor("apify/instagram-scraper").call(
        run_input={"resultsType": "details", "directUrls": [f"https://www.instagram.com/{usuario}/"]}
    )
    dataset_profile_id = run_profile.get("defaultDatasetId") or getattr(run_profile, "default_dataset_id", None)
    
    if dataset_profile_id:
        for item in client_apify.dataset(dataset_profile_id).iterate_items():
            with open(os.path.join(pasta, "insta_bio.txt"), "w", encoding="utf-8") as f:
                f.write(item.get("biography", "Sem biografia."))
            break

    run_posts = client_apify.actor("apify/instagram-scraper").call(
        run_input={"resultsType": "posts", "directUrls": [f"https://www.instagram.com/{usuario}/"], "resultsLimit": 6}
    )
    dataset_posts_id = run_posts.get("defaultDatasetId") or getattr(run_posts, "default_dataset_id", None)
    
    if dataset_posts_id:
        contador_img = 1
        for item in client_apify.dataset(dataset_posts_id).iterate_items():
            if contador_img > 6: break
            
            with open(os.path.join(pasta, f"insta_post_{contador_img}.txt"), "w", encoding="utf-8") as f:
                f.write(item.get("caption", "Sem legenda."))
                
            urls = item.get("carouselImages") or (item.get("images") if item.get("images") else [item.get("displayUrl")])
            if urls:
                for url in urls[:1]:
                    try:
                        resp = requests.get(url, timeout=10)
                        if resp.status_code == 200:
                            # Obriga a conversão de nomenclatura para .webp para o portfólio
                            with open(os.path.join(pasta, f"foto{contador_img}.webp"), "wb") as img_f:
                                img_f.write(resp.content)
                            contador_img += 1
                    except: pass

# =====================================================================
# 4. ENTRADA E ORQUESTRAÇÃO DO PIPELINE
# =====================================================================
colA, colB = st.columns(2)
with colA:
    input_empresa = st.text_input("📍 Instituição (Google Maps)", placeholder="Ex: Contabilidade Alpha")
with colB:
    input_insta = st.text_input("📸 Instagram (@)", placeholder="Ex: alpha_contabilidade")

if st.button("⚡ SINTETIZAR ESTRUTURA INSTITUCIONAL", use_container_width=True):
    if not input_empresa or not input_insta:
        st.warning("Forneça os dados de entrada para iniciar o motor.")
        st.stop()

    pasta_cliente = os.path.join("dados_empresas", input_empresa.replace("/", "-").replace(" ", "_"))
    os.makedirs(pasta_cliente, exist_ok=True)

    with st.status("Iniciando Pipeline de Arquitetura Institucional Epiverso...", expanded=True) as status:
        try:
            # --- FASE 1: RASPAGEM DE DADOS BRUTOS ---
            status.update(label="📍 Extraindo dados e provas sociais do Google Maps...")
            extrair_google_maps(input_empresa, pasta_cliente)
            
            status.update(label="📸 Mapeando portfólio e linguagem visual do Instagram...")
            extrair_instagram(input_insta.replace("@", ""), pasta_cliente)

            # --- FASE 2: PREPARAÇÃO DE CONTEXTO ---
            status.update(label="🧠 Preparando contexto isolado para a IA...")
            menu_raw = open("menu.txt", "r", encoding="utf-8").read() if os.path.exists("menu.txt") else "MENU NÃO ENCONTRADO"
            estrutura_raw = open("estrutura.txt", "r", encoding="utf-8").read() if os.path.exists("estrutura.txt") else "ESTRUTURA NÃO ENCONTRADA"
            
            contexto_cliente = ""
            for txt in glob.glob(os.path.join(pasta_cliente, "*.txt")):
                contexto_cliente += f"\n<arquivo_cliente nome='{os.path.basename(txt)}'>\n" + open(txt, "r", encoding="utf-8").read() + "\n</arquivo_cliente>"

            imagens_cliente = [Image.open(img) for img in glob.glob(os.path.join(pasta_cliente, "*.webp"))]

            # Roteamento Randômico de Estética (Prevenção de Convergência de Design)
            esteticas = ["Minimalismo Japandi (Tons terrosos, limpo)", "Neumórfico Corporativo (Sombras suaves, luxo branco)", "Clean Tech (Cinzento claro, formas secas)", "Glassmorphism Suave (Translúcido em fundo branco quente)"]
            estetica_sorteada = random.choice(esteticas)

            # --- FASE 3: MEGA PROMPT I (O ARQUITETO ESTRATÉGICO) ---
            status.update(label="📐 Desenhando Blueprint Arquitetural (Análise CoT)...")
            
            prompt_arquiteto = f"""
<system_persona>Atue como o Arquiteto Principal de Interfaces (UX/UI) e Especialista em Conversão Comercial do sistema Epiverso. A sua competência central é projetar páginas institucionais de alto valor para prestadores de serviços, cruzando a psicologia do consumidor com a estética minimalista e luxuosa.</system_persona>

<core_directives>
1. ESTRATÉGIA DE CONVERSÃO: Redija textos diretos, persuasivos e baseados na resolução de problemas extraídos dos <dados_cliente>. É imperativo evitar formulações robóticas e genéricas (como "Descubra soluções inovadoras"). O tom deve transmitir autoridade clínica ou corporativa.
2. ADAPTAÇÃO TEMÁTICA (LIGHT PREMIUM): A estética final exige obrigatoriamente um tema claro. O estilo visual exigido para este projeto é: **{estetica_sorteada}**. Você selecionará componentes que nativamente possam ser escuros, devendo planear e documentar as ordens exatas de inversão de propriedades de cor (fundos claros, textos escuros, sombras suaves) para o engenheiro subsequente.
3. SELEÇÃO DE COMPONENTES: O mapeamento entre a <estrutura_exigida> e o <catalogo_componentes> deve ser exato e cirúrgico.
4. LEITURA VISUAL: Analise as imagens enviadas e defina uma `--accent-color` (Cor de Destaque) no formato hexadecimal baseando-se na paleta dominante da identidade do cliente.
</core_directives>

<constraints>
- FIDELIDADE AO CATÁLOGO: É obrigatória a utilização exclusiva de identificadores de componentes que constem textualmente no <catalogo_componentes>.
- COMPREENSÃO POR CONTRASTE: 
  [Ação Rejeitada]: Escolher [ID: 999] por inferir que seria útil, apesar de não existir na lista fornecida. 
  [Ação Aprovada]: Analisar a necessidade de mostrar "Benefícios", percorrer a lista, encontrar o [ID: 059] - Benefits e instruir a sua adaptação para o tema claro.
</constraints>

<context>
  <estrutura_exigida>
  {estrutura_raw}
  </estrutura_exigida>
  <dados_cliente>
  {contexto_cliente}
  </dados_cliente>
  <catalogo_componentes>
  {menu_raw}
  </catalogo_componentes>
</context>

<task>
Sintetize as informações do <context> para traçar o perfil do prestador de serviço. Percorra meticulosamente a <estrutura_exigida> passo a passo. Para cada bloco lógico exigido, selecione o identificador numérico correspondente no <catalogo_componentes>. Após a seleção, redija o conteúdo persuasivo (Copy) para preencher a estrutura do componente e estipule as diretrizes de adaptação cromática para assegurar a consistência do Tema Claro.
</task>

<output_format>
Antes de materializar o projeto, execute uma decomposição lógica do seu planeamento dentro da etiqueta <analise_estrategica>, justificando as suas escolhas passo a passo. Após a análise, forneça o projeto final seguindo escrupulosamente a formatação exigida em Markdown.

<analise_estrategica>
1. Diagnóstico do Público: [Avaliação das dores e necessidades baseadas no Maps/Instagram].
2. Lógica Cromática: [Justificação para as cores extraídas das imagens].
3. Mapeamento Lógico: [Associação de cada secção da estrutura ao ID específico do catálogo].
</analise_estrategica>

# 🎨 IDENTIDADE VISUAL E TOKENS DA PÁGINA
* **Tema**: Light Premium / {estetica_sorteada}
* **Paleta de Cores Gerada**:
  * `--bg-page`: [Hexadecimal muito claro]
  * `--text-main`: [Hexadecimal escuro para contraste]
  * `--accent-color`: [Hexadecimal vibrante extraído das imagens]
* **Tipografia (Google Fonts)**: [Duas fontes elegantes]

# 🏗️ BLUEPRINT DA PÁGINA (ESTRUTURA)
## 1. [Nome da Secção conforme Estrutura Exigida]
* **Blocos Escolhidos**: [ID: XXX] - [Nome literal do bloco no catálogo]
* **Instruções de Adaptação (Design)**: [Diretriz exata para converter o bloco de Dark para Light Premium]
* **Copywriting**:
  * **Kicker/Eyebrow**: "..."
  * **Título Principal**: "..."
  * **Subtítulo/Texto de Apoio**: "..."
  * **Call to Action (Botão)**: "..."
  * **Elementos Adicionais**: "..."
</output_format>
"""
            
            # Temperatura elevada para permitir fluidez no Copywriting (0.35)
            blueprint_response = client_gemini.models.generate_content(
                model='gemini-3.5-flash',
                contents=[prompt_arquiteto] + imagens_cliente,
                config=types.GenerateContentConfig(temperature=0.35)
            )
            
            with open(os.path.join(pasta_cliente, "blueprint_estrategico.md"), "w", encoding="utf-8") as f:
                f.write(blueprint_response.text)

            # --- FASE 4: COLETOR DE FONTES ---
            status.update(label="🔎 Coletando fragmentos de código-fonte mapeados no Blueprint...")
            ids_selecionados = list(set(re.findall(r'\[ID:\s*(\d+)\]', blueprint_response.text)))
            
            codigo_dos_blocos = ""
            for comp_id in ids_selecionados:
                for arq in glob.glob(f"*{comp_id}*.txt"):
                    codigo_dos_blocos += f"\n\n<!-- === BLOCO FONTE [ID: {comp_id}] === -->\n"
                    codigo_dos_blocos += open(arq, "r", encoding="utf-8").read()

            if not codigo_dos_blocos:
                st.warning("Aviso: Nenhum código fonte local (.txt) contendo os IDs mapeados foi encontrado no diretório.")

            # --- FASE 5: MEGA PROMPT II (ENGENHEIRO FRONT-END) ---
            status.update(label="⚙️ Sintetizando HTML/CSS/JS (Engenharia de Compilação Estrita)...")

            prompt_engenheiro = f"""
<system_persona>Atue como um Engenheiro Frontend Especialista e Arquiteto de Sistemas de Interface da Epiverso. Possui domínio absoluto sobre manipulação de DOM, propriedades CSS variáveis e arquitetura de animações.</system_persona>

<core_constraints>
[IMPORTANTE]: O seu objetivo primário é a COMPILAÇÃO e MONTAGEM MASSIVA.
1. PROIBIDO ECONOMIZAR CÓDIGO: O script deve ser escrito de fora a fora. Não use abreviações ou comentários vazios como "<!-- adicione o resto aqui -->". Eu preciso do código completo.
2. INTOCABILIDADE ESTRUTURAL: É proibido alterar a hierarquia das etiquetas HTML dos blocos originais, eliminar classes existentes ou reescrever a arquitetura das divisórias (`divs`). A geometria já está perfeita. Posicione os blocos e injete a copy providenciada.
3. BANIMENTO DE FRAMEWORKS EXTERNOS: Todo o código deve operar nativamente. Proibida a inclusão de Tailwind CSS, React ou Bootstrap.
4. CONVERSÃO DE TEMAS (DARK PARA LIGHT PREMIUM): A maioria dos blocos fornecidos tem génese no modo escuro. O seu dever é aplicar engenharia inversa nas variáveis cromáticas.
   - Sombreados profundos (`rgba(0,0,0,0.8)`) devem ser brutalmente diluídos para `rgba(0,0,0,0.04)`.
   - Efeitos de "Glassmorphism" negros devem transitar para fundos brancos translúcidos (`rgba(255,255,255,0.7)`) mantendo o desfoque (`backdrop-filter`).
5. ASSINATURA EPIVERSO: No footer final, inclua ESTRITAMENTE: Desenvolvido por <a href="https://epiverso.com" target="_blank" style="color: var(--accent-color); font-weight: bold; text-decoration: none;">EPIVERSO</a>.
6. IMAGENS WEBP: Ao renderizar imagens do portfólio, use ESTRITAMENTE a nomenclatura foto1.webp, foto2.webp...
</core_constraints>

<context>
  <projeto_arquitetonico>
  {blueprint_response.text}
  </projeto_arquitetonico>
  <componentes_fonte>
  {codigo_dos_blocos}
  </componentes_fonte>
</context>

<task>
1. Extraia a paleta de cores e tipografia do <projeto_arquitetonico> e converta-as num seletor `:root` unificado no HTML final.
2. Inicie a montagem do ficheiro `index.html` substituindo o placeholder de textos e imagens pelas diretrizes exatas do Blueprint.
3. Agregue todos os fragmentos de CSS na tag `<style>`, certificando-se de que a lógica de inversão de cor é aplicada.
4. Centralize toda a lógica JavaScript na tag `<script>` ao final do body.
</task>

<output_format>
Antes da geração final do código, planeie a fusão executando uma <verificacao_de_sintese>, identificando possíveis conflitos na união dos blocos (como z-index de stickys e transparências) e garantindo que o plano de cores respeita o limite do tema Light Premium exigido.
A sua resposta deve conter estritamente o bloco de código HTML unificado (com CSS e JS embutidos) formatado da seguinte forma:

<verificacao_de_sintese>
- Conflitos de CSS identificados: ...
- Validação de conversão Dark to Light: ...
- Validação de nomenclatura Webp: ...
</verificacao_de_sintese>

```html
<!DOCTYPE html>
<html lang="pt-BR">
<!-- Estrutura massiva, exaustiva e completa montada -->
</html>'''
