import streamlit as st
import os
import requests
from apify_client import ApifyClient
import glob
import re
from google import genai
from google.genai import types
from PIL import Image
import shutil

# ==========================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(page_title="Epiverso | Gerador Institucional", page_icon="🚀", layout="wide")

# CSS CUSTOMIZADO PREMIUM EPIVERSO (Injetado sem afetar a lógica base)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stButton>button {
            background-color: #111827;
            color: white;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            border: 1px solid #374151;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #1F2937;
            border-color: #9CA3AF;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Gerador de Páginas Institucionais Premium - Epiverso")
st.markdown("Insira os dados do prestador de serviço abaixo para raspar as informações e orquestrar a montagem da página de altíssima conversão.")

# ==========================================
# PUXANDO AS CHAVES EM MODO INVISÍVEL (BACKEND)
# ==========================================
try:
    apify_token = st.secrets["APIFY_TOKEN"]
    gemini_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    apify_token = None
    gemini_key = None
    st.error("⚠️ Configuração de sistema ausente: As chaves de API não foram encontradas no servidor.")

# ==========================================
# BARRA LATERAL (INFORMAÇÕES DO SISTEMA)
# ==========================================
with st.sidebar:
    st.header("⚙️ Motor Epiverso")
    st.info("Este gerador utiliza inteligência artificial avançada e web scraping para estruturar landing pages premium baseadas em dados reais.")
    
    st.header("📂 Estrutura Necessária")
    st.success("✔ menu.txt\n✔ estrutura.txt\n✔ Biblioteca de Componentes")

# ==========================================
# ENTRADA DE DADOS DO CLIENTE
# ==========================================
col1, col2 = st.columns(2)
with col1:
    empresa_alvo = st.text_input("📍 Nome da Empresa (Google Maps)", value="Dentista no Passo de Torres | Dra. Daiane Medeiros")
with col2:
    instagram_alvo = st.text_input("📸 Usuário do Instagram (sem @)", value="dra_daiane_medeiros")

# ==========================================
# FUNÇÃO PARA COMPACTAR ARQUIVOS FINAIS
# ==========================================
def zip_directory(folder_path, zip_path):
    shutil.make_archive(zip_path, 'zip', folder_path)

# ==========================================
# BOTÃO DE EXECUÇÃO
# ==========================================
if st.button("⚡ Gerar Página Institucional Premium", type="primary", use_container_width=True):
    if not apify_token or not gemini_key:
        st.error("⚠️ As chaves da API do Apify e do Gemini são obrigatórias!")
    else:
        with st.status("Iniciando esteira de produção da Epiverso...", expanded=True) as status:
            try:
                # ---------------------------------------------------------
                # 1. PREPARAÇÃO DE PASTAS E APIS
                # ---------------------------------------------------------
                client_apify = ApifyClient(apify_token)
                client_gemini = genai.Client(api_key=gemini_key)
                
                pasta_base = "dados_empresas"
                pasta_destino = os.path.join(pasta_base, empresa_alvo.replace("/", "-").replace(" ", "_"))
                os.makedirs(pasta_destino, exist_ok=True)
                
                # ---------------------------------------------------------
                # 2. BUSCA NO GOOGLE MAPS
                # ---------------------------------------------------------
                status.update(label=f"📍 Buscando avaliações no Maps para: '{empresa_alvo}'...")
                maps_input = {
                    "searchStringsArray": [empresa_alvo],
                    "maxCrawledPlacesPerSearch": 1,
                    "scrapePlaceDetailPage": True,
                    "maxReviews": 5,
                    "reviewsSort": "highestRanking",
                    "scrapeContacts": False
                }
                run_maps = client_apify.actor("compass/crawler-google-places").call(run_input=maps_input)
                dataset_maps_id = run_maps.get("defaultDatasetId") if isinstance(run_maps, dict) else getattr(run_maps, "defaultDatasetId", getattr(run_maps, "default_dataset_id", None))
                
                if dataset_maps_id:
                    for place in client_apify.dataset(dataset_maps_id).iterate_items():
                        nome_empresa = place.get("title", empresa_alvo)
                        reviews = place.get("reviews", [])
                        textos_reviews = []
                        for r in reviews[:5]:
                            nota = r.get("stars", 5)
                            nome_avaliador = r.get("name", "Anônimo")
                            texto = r.get("text", "").replace("\n", " ")
                            if texto:
                                textos_reviews.append(f"[{nota}⭐] {nome_avaliador} comentou: {texto}")
                                
                        if textos_reviews:
                            caminho_avaliacoes_txt = os.path.join(pasta_destino, "avaliacoes_google.txt")
                            with open(caminho_avaliacoes_txt, "w", encoding="utf-8") as f:
                                f.write(f"Avaliações - {nome_empresa}\n")
                                f.write("="*40 + "\n\n")
                                for review in textos_reviews:
                                    f.write(f"{review}\n\n")
                            st.write(f"📄 Avaliações do Maps salvas!")
                        break

                # ---------------------------------------------------------
                # 3. BUSCA NO INSTAGRAM
                # ---------------------------------------------------------
                status.update(label=f"📸 Buscando dados e posts do Instagram de: @{instagram_alvo}...")
                run_input_profile = {"resultsType": "details", "directUrls": [f"https://www.instagram.com/{instagram_alvo}/"]}
                run_profile = client_apify.actor("apify/instagram-scraper").call(run_input=run_input_profile)
                
                dataset_profile_id = run_profile.get("defaultDatasetId") if isinstance(run_profile, dict) else getattr(run_profile, "defaultDatasetId", getattr(run_profile, "default_dataset_id", None))
                
                if dataset_profile_id:
                    for item in client_apify.dataset(dataset_profile_id).iterate_items():
                        bio = item.get("biography", "")
                        caminho_bio = os.path.join(pasta_destino, f"{instagram_alvo}_bio.txt")
                        with open(caminho_bio, "w", encoding="utf-8") as arquivo:
                            arquivo.write(bio if bio else "Perfil sem biografia ou descrição.")
                        
                        perfil_url = item.get("profilePicUrlHD") or item.get("profilePicUrl")
                        if perfil_url:
                            try:
                                resp = requests.get(perfil_url, timeout=10)
                                if resp.status_code == 200:
                                    caminho_perfil = os.path.join(pasta_destino, f"{instagram_alvo}_perfil.jpg")
                                    with open(caminho_perfil, "wb") as arquivo:
                                        arquivo.write(resp.content)
                            except Exception as e:
                                st.write(f"❌ Erro ao baixar foto de perfil: {e}")
                        break

                LIMITE_POSTS_DESEJADOS = 5
                run_input_posts = {"resultsType": "posts", "directUrls": [f"https://www.instagram.com/{instagram_alvo}/"], "resultsLimit": LIMITE_POSTS_DESEJADOS}
                run_posts = client_apify.actor("apify/instagram-scraper").call(run_input=run_input_posts)
                
                dataset_posts_id = run_posts.get("defaultDatasetId") if isinstance(run_posts, dict) else getattr(run_posts, "defaultDatasetId", getattr(run_posts, "default_dataset_id", None))
                
                if dataset_posts_id:
                    contador_post = 1
                    contador_foto_global = 1 # Garante a nomenclatura sequencial foto1.webp
                    for item in client_apify.dataset(dataset_posts_id).iterate_items():
                        if contador_post > LIMITE_POSTS_DESEJADOS: break
                        urls_para_baixar = item.get("carouselImages") if item.get("type") == "Sidecar" and item.get("carouselImages") else item.get("images") if item.get("images") else [item.get("displayUrl")] if item.get("displayUrl") else []
                        
                        if urls_para_baixar:
                            legenda = item.get("caption", "")
                            caminho_legenda = os.path.join(pasta_destino, f"post_{contador_post}_legenda.txt")
                            with open(caminho_legenda, "w", encoding="utf-8") as arquivo:
                                arquivo.write(legenda if legenda else "Postagem sem legenda.")
                            
                            for idx, url_imagem in enumerate(urls_para_baixar):
                                try:
                                    resposta = requests.get(url_imagem, timeout=10)
                                    if resposta.status_code == 200:
                                        # Salvando forçadamente em .webp e na ordem exata solicitada
                                        caminho_arquivo = os.path.join(pasta_destino, f"foto{contador_foto_global}.webp")
                                        with open(caminho_arquivo, "wb") as arquivo:
                                            arquivo.write(resposta.content)
                                        contador_foto_global += 1
                                except: pass
                            contador_post += 1
                st.write("✅ Dados e mídias do Instagram extraídos!")

                # ---------------------------------------------------------
                # 4. ORQUESTRADOR IA (BLUEPRINT)
                # ---------------------------------------------------------
                status.update(label="🧠 Analisando dados e gerando Blueprint de Arquitetura...")
                
                menu_componentes = open("menu.txt", "r", encoding="utf-8").read() if os.path.exists("menu.txt") else st.warning("Aviso: 'menu.txt' não encontrado!")
                estrutura_pagina = open("estrutura.txt", "r", encoding="utf-8").read() if os.path.exists("estrutura.txt") else st.warning("Aviso: 'estrutura.txt' não encontrado!")
                
                dados_compilados = ""
                caminho_avaliacoes = os.path.join(pasta_destino, "avaliacoes_google.txt")
                if os.path.exists(caminho_avaliacoes):
                    dados_compilados += "--- AVALIAÇÕES DO GOOGLE MAPS ---\n" + open(caminho_avaliacoes, "r", encoding="utf-8").read() + "\n\n"
                
                arquivos_bio = glob.glob(os.path.join(pasta_destino, "*_bio.txt"))
                if arquivos_bio:
                    dados_compilados += "--- BIO DO INSTAGRAM ---\n" + open(arquivos_bio[0], "r", encoding="utf-8").read() + "\n\n"
                
                arquivos_legendas = glob.glob(os.path.join(pasta_destino, "*_legenda.txt"))
                if arquivos_legendas:
                    dados_compilados += "--- ÚLTIMOS POSTS DO INSTAGRAM ---\n"
                    for arquivo in arquivos_legendas:
                        dados_compilados += f"[{os.path.basename(arquivo)}]:\n{open(arquivo, 'r', encoding='utf-8').read()}\n\n"
                
                arquivos_imagens = glob.glob(os.path.join(pasta_destino, "*.jpg")) + glob.glob(os.path.join(pasta_destino, "*.webp"))
                imagens_para_ia = [Image.open(img) for img in arquivos_imagens]
                
                prompt = f"""
                Você é o Arquiteto de UI/UX, Diretor de Arte Chefe e Copywriter Master da Epiverso.

                Sua missão é criar o "Blueprint" de uma Landing Page de Alta Conversão.
                Analise os dados extraídos para determinar o nicho exato do cliente e, com base nisso, defina a identidade visual e o tom da copy.

                REGRAS DE DESIGN E UX GUIADAS PELO NICHO:
                - Nicho fofo/descontraído (ex: pet shop, infantil): Bordas arredondadas (border-radius alto), cores vibrantes, tipografia amigável e tom de voz acolhedor.
                - Nicho sério/corporativo (ex: advocacia, contabilidade): Formas retas, cantos quadrados, cores sóbrias (azul marinho, dourado, cinza), tipografia serifada ou elegante e tom de voz incisivo.
                - Nicho intermediário (ex: estética, unhas, arquitetura): Equilibre elegância com modernidade.
                - ATENÇÃO AO PORTFÓLIO: Recomende a seção de Galeria de Fotos APENAS se o nicho for visual. Se for estritamente corporativo ou consultivo, NÃO crie e instrua o dev a ignorar a galeria.
                
                Siga a ESTRUTURA DA PÁGINA e escolha no MENU DE COMPONENTES os blocos perfeitos pelo [ID]. Escreva a copy voltada para conversão baseada nas dores/revisões extraídas. Defina no final a paleta de cores.

                =========================================
                📄 MENU DE COMPONENTES (BIBLIOTECA EPIVERSO):
                {menu_componentes}
                =========================================
                📋 ESTRUTURA DA PÁGINA EXIGIDA:
                {estrutura_pagina}
                =========================================
                🧠 DADOS DO CLIENTE (PARA COPY E IDENTIDADE VISUAL):
                {dados_compilados}
                """
                instrucoes_epiverso = "Você é o Arquiteto Front-End Master da Epiverso. Siga as orientações à risca, escolhendo IDs válidos e criando a identidade baseada no nicho exato do cliente."
                
                conteudo_completo = [prompt] + imagens_para_ia
                resposta_blueprint = client_gemini.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=conteudo_completo,
                    config=types.GenerateContentConfig(system_instruction=instrucoes_epiverso, temperature=0.3)
                )
                
                caminho_blueprint = os.path.join(pasta_destino, "blueprint_landing_page.md")
                with open(caminho_blueprint, "w", encoding="utf-8") as f:
                    f.write(resposta_blueprint.text)
                st.write("✅ Blueprint gerado com sucesso!")

                # ---------------------------------------------------------
                # 5. ENGENHEIRO IA (GERAÇÃO DE CÓDIGO EXAUSTIVO)
                # ---------------------------------------------------------
                status.update(label="🧩 Montando componentes e gerando o código final...")
                
                ids_encontrados = list(set(re.findall(r'\[ID:\s*(\d+)\]', resposta_blueprint.text)))
                codigos_componentes = ""
                for comp_id in ids_encontrados:
                    arquivos_match = glob.glob(f"*{comp_id}*.txt")
                    for arq in arquivos_match:
                        codigos_componentes += f"\n\n=========================================\n--- CÓDIGO FONTE DO BLOCO [ID: {comp_id}] (Arquivo: {arq}) ---\n=========================================\n" + open(arq, "r", encoding="utf-8").read()

                prompt_programador = f"""
                Atue como um Desenvolvedor Front-end Sênior e Copywriter Especialista em Landing Pages de Alta Conversão da Epiverso.
                A partir das informações do Blueprint e dos Códigos dos Componentes fornecidos, escreva o código completo de uma Landing Page em um único arquivo index.html (com todo o CSS embutido na tag <style> e JS no final do <body> em <script>).

                REGRAS DE DESENVOLVIMENTO (SIGA RIGOROSAMENTE - EXTREMAMENTE IMPORTANTE):
                1. PROIBIDO ECONOMIZAR CÓDIGO: Escreva o script de fora a fora. Não abrevie o código, não crie módulos incompletos e não use placeholders como "adicione o resto aqui" ou "<!-- mais conteúdo -->". A página TEM QUE VIR 100% pronta.
                2. Fidelidade ao Nicho: Adapte a identidade visual estritamente às indicações do Blueprint.
                3. Tecnologia e Animações Modernas: Utilize variáveis CSS no :root. Inclua animações fluidas, efeitos de hover avançados, bibliotecas como AOS.js. Fuja do design que parece "gerado por IA".
                4. SEO e Gatilhos: Adicione Meta Tags otimizadas, botões flutuantes e fixos do WhatsApp pulsantes e estruturação semântica do HTML (h1, h2, seções claras).
                5. ASSINATURA OBRIGATÓRIA DA AGÊNCIA: No Footer, inclua os direitos reservados do cliente e adicione a assinatura EXATA: Desenvolvido por <a href="https://epiverso.com" target="_blank" style="color: var(--secondary, #000); font-weight: bold; text-decoration: none;">EPIVERSO</a>.
                6. GALERIA DE FOTOS: Quando o nicho exigir, chame as imagens da galeria EXATAMENTE COM ESTA NOMENCLATURA: foto1.webp, foto2.webp, foto3.webp... 
                7. O site deve sempre ser extremamente responsivo, para celulares, tabletes e computadores.

                =========================================
                📄 BLUEPRINT DA PÁGINA:
                {resposta_blueprint.text}

                =========================================
                🧩 CÓDIGOS FONTES DOS COMPONENTES (PARA VOCÊ MONTAR):
                {codigos_componentes}
                """
                instrucoes_dev = "Você é um Engenheiro de Software Sênior implacável. Gere um código gigantesco e exaustivo se for preciso, mas ENTREGUE PRONTO. Não abrevie. Siga as regras de UI/UX, nicho e conversão do prompt perfeitamente."
                
                resposta_codigo = client_gemini.models.generate_content(
                    model='gemini-3.5-pro',
                    contents=prompt_programador,
                    config=types.GenerateContentConfig(system_instruction=instrucoes_dev, temperature=0.1)
                )
                st.write("✅ Código fonte exaustivo escrito com sucesso!")

                # ---------------------------------------------------------
                # 6. EXTRATOR DE CÓDIGO E EMPACOTAMENTO
                # ---------------------------------------------------------
                status.update(label="📂 Extraindo arquivos e preparando o pacote final...")
                
                pasta_saida = "landing_page_pronta"
                os.makedirs(pasta_saida, exist_ok=True)
                
                match_html = re.search(r'```html(.*?)```', resposta_codigo.text, re.DOTALL | re.IGNORECASE)
                if match_html:
                    codigo_final = match_html.group(1).strip()
                else:
                    codigo_final = resposta_codigo.text.replace('```html', '').replace('```', '').strip()

                with open(os.path.join(pasta_saida, "index.html"), "w", encoding="utf-8") as arquivo:
                    arquivo.write(codigo_final)
                
                zip_path = "landing_page_pronta"
                zip_directory(pasta_saida, zip_path)
                
                status.update(label="🚀 Tudo pronto! Site compilado de ponta a ponta.", state="complete")
            
            except Exception as e:
                status.update(label="❌ Ocorreu um erro no processo", state="error")
                st.error(f"Erro: {e}")

    # ==========================================
    # RESULTADO E DOWNLOAD
    # ==========================================
    if os.path.exists("landing_page_pronta.zip"):
        st.success(f"A Landing Page de alta conversão de **{empresa_alvo}** foi orquestrada com sucesso!")
        
        with open("landing_page_pronta.zip", "rb") as fp:
            st.download_button(
                label="📦 Baixar Código Final (.ZIP)",
                data=fp,
                file_name=f"{instagram_alvo}_landing_page_epiverso.zip",
                mime="application/zip",
                type="primary"
            )
        
        if 'resposta_blueprint' in locals():
            with st.expander("Ver Blueprint Arquitetural Gerado"):
                st.markdown(resposta_blueprint.text)
    else:
        st.warning("⚠️ O arquivo .zip não foi gerado. Verifique a caixa de status acima.")
