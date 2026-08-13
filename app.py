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
st.title("🚀 Gerador de Páginas Institucionais Premium - Epiverso")
st.markdown("Insira os dados do prestador de serviço abaixo para raspar as informações e orquestrar a montagem da página.")

# ==========================================
# BARRA LATERAL (CONFIGURAÇÕES E CHAVES)
# ==========================================
with st.sidebar:
    st.header("🔑 Configurações de API")
    apify_token = st.text_input("Apify API Token", value="apify_api_HrvGIIfKg85b3my2mKw1LemyZnbK134kJQbr", type="password")
    gemini_key = st.text_input("Gemini API Key", value="AIzaSyCAMwvIyo1fRIjdrHPVFTwbIds2COS7Rng", type="password")
    
    st.header("📂 Arquivos Base Necessários")
    st.info("Certifique-se de que os arquivos `menu.txt`, `estrutura.txt` e os `.txt` dos componentes estão na mesma pasta que este script.")

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
if st.button("⚡ Gerar Página Institucional", type="primary", use_container_width=True):
    if not apify_token or not gemini_key:
        st.error("⚠️ As chaves da API do Apify e do Gemini são obrigatórias!")
    else:
        # Cria um container de status para dar feedback visual em tempo real
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
                                        caminho_arquivo = os.path.join(pasta_destino, f"post_{contador_post}_foto_{idx+1}.jpg")
                                        with open(caminho_arquivo, "wb") as arquivo:
                                            arquivo.write(resposta.content)
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
                
                arquivos_imagens = glob.glob(os.path.join(pasta_destino, "*.jpg"))
                imagens_para_ia = [Image.open(img) for img in arquivos_imagens]
                
                prompt = f"""
Você é o Arquiteto de UI/UX, Diretor de Arte Chefe e Copywriter Master da Epiverso.

Sua missão é criar o "Blueprint" (Projeto Arquitetônico) de uma Landing Page High-Ticket para prestadores de serviço. O design OBRIGATORIAMENTE deve seguir um Tema Claro (Light Theme), transmitindo limpeza, luxo, confiança e autoridade clínica/corporativa (brancos quentes, beges, cinzas claros e uma cor de destaque sóbria).

Você recebeu três conjuntos de informações cruciais:
1. DADOS DO CLIENTE: Avaliações, dores, elogios, bio e imagens. Analise isso para criar a Copy e a Paleta de Cores.
2. ESTRUTURA DA PÁGINA: A ordem exata das seções que precisamos criar.
3. MENU DE COMPONENTES: A nossa biblioteca proprietária de blocos e componentes catalogados por [ID] numérico.

=== SEU OBJETIVO DESTRINCHADO ===
1. Entenda quem é o cliente e qual o seu público-alvo a partir das fotos e textos.
2. Siga a ESTRUTURA DA PÁGINA passo a passo.
3. Para cada passo da ESTRUTURA, vá ao MENU DE COMPONENTES e ESCOLHA O MELHOR BLOCO pelo seu [ID] exato (Ex: [ID: 210], [ID: 254], etc).
4. Escreva o COPYWRITING completo (Títulos, Textos e CTAs) focado em alta conversão e na resolução das dores extraídas do Google Maps.
5. Indique as adaptações de CORES necessárias nos tokens do bloco para encaixar no "Tema Claro Premium" do cliente.

=== REGRAS ABSOLUTAS ===
- É ESTritamente PROIBIDO alucinar ou inventar [IDs] que não estejam no MENU DE COMPONENTES.
- Você tem LIBERDADE TOTAL para instruir a alteração das cores dos blocos escolhidos (transformando blocos dark em light), desde que a estrutura mecânica do bloco permaneça a mesma.
- A Copy (texto) não pode ter palavras clichês de IA (ex: "Descubra", "Soluções Inovadoras"). Use tom humano, direto, focado em autoridade e resultado.

FORMATO DE SAÍDA EXIGIDO (Siga esta formatação em Markdown rigorosamente):

# 🎨 IDENTIDADE VISUAL E TOKENS DA PÁGINA
* **Tema**: Light Premium / Service Professional
* **Paleta de Cores Gerada**:
  * `--bg-page`: [Sugira Hex Claro, ex: #F8F9FA]
  * `--text-main`: [Sugira Hex Escuro, ex: #111827]
  * `--accent-color`: [Sugira Hex de Destaque baseado nas fotos/nicho do cliente]
* **Tipografia (Google Fonts)**: [Sugira 2 fontes elegantes. Ex: 'Cormorant Garamond' para display, 'Inter' para corpo]

# 🏗️ BLUEPRINT DA PÁGINA (ESTRUTURA)

## 1. [NOME DA SEÇÃO BASEADO NA ESTRUTURA.TXT]
* **Blocos  Escolhidos**: ex: [ID: XXX] - [Nome do Bloco]
* **Componentes Internos Exigidos**: [IDs de botões, cards ou espaçadores, se houver]
* **Instruções de Adaptação (Design)**: [Como o dev deve pintar ou adaptar este bloco para o tema claro]
* **Copywriting**:
  * **Kicker/Eyebrow**: "..."
  * **Título Principal (H1/H2)**: "..."
  * **Subtítulo/Apoio**: "..."
  * **CTA (Botão)**: "..."

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
                instrucoes_epiverso = """
Você é o Arquiteto Front-End Master da Epiverso.
Sua única função é montar o Blueprint da Landing Page combinando os DADOS DO CLIENTE com os blocos exatos do MENU DE COMPONENTES, guiado pela ESTRUTURA DA PÁGINA.
NUNCA invente códigos CSS ou HTML nesta etapa. Gere APENAS o documento Markdown solicitado contendo os [IDs], as Cores adaptadas para Light Theme e a Copywriting de alta conversão. Seja um estrategista de vendas implacável na escrita dos textos.
"""
                conteudo_completo = [prompt] + imagens_para_ia
                resposta_blueprint = client_gemini.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=conteudo_completo,
                    config=types.GenerateContentConfig(system_instruction=instrucoes_epiverso, temperature=0.3)
                )
                
                caminho_blueprint = os.path.join(pasta_destino, "blueprint_landing_page.md")
                with open(caminho_blueprint, "w", encoding="utf-8") as f:
                    f.write(resposta_blueprint.text)
                st.write("✅ Blueprint gerado com sucesso!")

                # ---------------------------------------------------------
                # 5. ENGENHEIRO IA (GERAÇÃO DE CÓDIGO)
                # ---------------------------------------------------------
                status.update(label="🧩 Montando componentes e gerando o código final...")
                
                ids_encontrados = list(set(re.findall(r'\[ID:\s*(\d+)\]', resposta_blueprint.text)))
                codigos_componentes = ""
                for comp_id in ids_encontrados:
                    arquivos_match = glob.glob(f"*{comp_id}*.txt")
                    for arq in arquivos_match:
                        codigos_componentes += f"\n\n=========================================\n--- CÓDIGO FONTE DO BLOCO [ID: {comp_id}] (Arquivo: {arq}) ---\n=========================================\n" + open(arq, "r", encoding="utf-8").read()

                prompt_programador = f"""
Você é um Engenheiro Front-End Sênior e Arquiteto CSS/GSAP de altíssimo nível.

Sua missão é construir uma Landing Page Premium de altíssima conversão, montando um "quebra-cabeça" de código.

Você está recebendo DOIS insumos:
1. O "BLUEPRINT DA PÁGINA": Que dita a paleta de cores Light Theme, tipografia, a cópia (textos) e a ordem dos blocos.
2. OS "CÓDIGOS DOS COMPONENTES": Os códigos base (HTML/CSS/JS) dos blocos pré-fabricados solicitados pelo Blueprint.

=== AS 5 REGRAS DE OURO DA ENGENHARIA ===
1. FIDELIDADE ESTRUTURAL ABSOLUTA: Use a estrutura HTML e as classes CSS exatas fornecidas nos códigos dos blocos. É ESTRITAMENTE PROIBIDO inventar novas seções ou alterar o esqueleto do DOM. Não use frameworks (Tailwind, Bootstrap).

2. ADAPTAÇÃO DE TEMA (DARK PARA LIGHT PREMIUM):
Os códigos originais fornecidos costumam ser de um "Dark Mode". Você DEVE inverter as propriedades de cor para refletir o Tema Claro exigido no Blueprint.
-> Iniba fundos escuros. Use a paleta do Blueprint (ex: `--bg-page`).
-> Suavize as sombras (box-shadow) para o tema claro (ex: use rgba com 0.05 de opacidade).
-> Converta botões para a `--accent-color` exigida.

3. INJEÇÃO DE COPYWRITING: Substitua os textos "Lorem Ipsum" dos códigos originais EXATAMENTE pela Copy fornecida no Blueprint.

4. ARQUITETURA CSS: Crie um `:root` unificando as variáveis de cores e tipografia ditadas pelo Blueprint e aplique-as nos blocos.

5. FLUXO JAVASCRIPT: Unifique a lógica JS dos blocos (GSAP, ScrollTrigger, Carrossel) em um único script estruturado.

ENTREGUE APENAS CÓDIGO. Divida sua resposta claramente em blocos Markdown para `index.html`, `style.css` e `script.js`.

=========================================
📄 BLUEPRINT DA PÁGINA:
{resposta_blueprint.text}

=========================================
🧩 CÓDIGOS FONTES DOS COMPONENTES (PARA VOCÊ MONTAR):
{codigos_componentes}
"""
                instrucoes_dev = """
Você é um compilador de código rigoroso.
Não converse, não explique. Apenas receba os blocos de código, mude as variáveis de cor para o Tema Claro, injete os textos do Blueprint e devolva os arquivos index.html, style.css e script.js prontos.
"""
                resposta_codigo = client_gemini.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt_programador,
                    config=types.GenerateContentConfig(system_instruction=instrucoes_dev, temperature=0.1)
                )
                st.write("✅ Código fonte escrito com sucesso!")

                # ---------------------------------------------------------
                # 6. EXTRATOR DE CÓDIGO
                # ---------------------------------------------------------
                status.update(label="📂 Extraindo arquivos e preparando o pacote final...")
                
                pasta_saida = "landing_page_pronta"
                os.makedirs(pasta_saida, exist_ok=True)
                
                match_html = re.search(r'```html(.*?)```', resposta_codigo.text, re.DOTALL | re.IGNORECASE)
                match_css = re.search(r'```css(.*?)```', resposta_codigo.text, re.DOTALL | re.IGNORECASE)
                match_js = re.search(r'```(?:javascript|js)(.*?)```', resposta_codigo.text, re.DOTALL | re.IGNORECASE)
                
                def salvar_arquivo(nome_arquivo, match_obj):
                    if match_obj:
                        with open(os.path.join(pasta_saida, nome_arquivo), "w", encoding="utf-8") as arquivo:
                            arquivo.write(match_obj.group(1).strip())
                
                salvar_arquivo("index.html", match_html)
                salvar_arquivo("style.css", match_css)
                salvar_arquivo("script.js", match_js)
                
                # Zipa os arquivos para download
                zip_path = "landing_page_pronta"
                zip_directory(pasta_saida, zip_path)
                
                status.update(label="🚀 Tudo pronto! Site compilado.", state="complete")
            
            except Exception as e:
                status.update(label="❌ Ocorreu um erro no processo", state="error")
                st.error(f"Erro: {e}")

        # ==========================================
        # RESULTADO E DOWNLOAD
        # ==========================================
        st.success(f"A página de **{empresa_alvo}** foi montada com sucesso!")
        
        with open("landing_page_pronta.zip", "rb") as fp:
            st.download_button(
                label="📦 Baixar Código Final (.ZIP)",
                data=fp,
                file_name=f"{instagram_alvo}_landing_page.zip",
                mime="application/zip",
                type="primary"
            )
        
        with st.expander("Ver Blueprint Gerado"):
            st.markdown(resposta_blueprint.text)