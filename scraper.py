import os
import time
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HISTORY_FILE = "sent_jobs.txt"

# PALAVRAS-CHAVE EXATAS DE BUSCA
KEYWORDS = [
    '"Segurança de Barragem"',
    '"Segurança de Barragens"',
    '"Construção de Barragens"',
    '"Construções de Barragens"',
    '"Obra de barragem"',
    '"Obras de Barragens"'
]

# Termos que OBRIGATORIAMENTE precisam indicar trabalho com BARRAGENS / PRESAS
MANDATORY_DAM_TERMS = [
    "barragem", "barragens", "presa", "presas"
]

# Termos de ação/escopo obrigatórios
MANDATORY_SCOPE_TERMS = [
    "segurança", "seguranca", "obra", "obras", "construção", "construcao", "construções", "construcoes"
]

# Lista Negra Rígida: Elimina qualquer vaga de Segurança do Trabalho / TI / Outros
STRICT_EXCLUDE_TERMS = [
    "trabalho", "laboral", "ocupacional", "hst", "sst", "medicina", "so",
    "patrimonial", "informação", "informacao", "ti", "dados", "cyber",
    "física", "fisica", "corporativa", "veicular", "privacidade", "pública", "publica",
    "alimentos", "bancária", "bancaria", "rede", "sistemas"
]

# WHITELIST ÚNICA E EXCLUSIVA (Apenas Brasil, Portugal e Espanha)
ALLOWED_REGIONS = [
    # Nomes dos Países
    "brasil", "brazil", "portugal", "espanha", "spain", "españa",
    
    # Brasil (Siglas dos Estados e Capitais Principais)
    "sp", "mg", "rj", "pa", "ba", "go", "mt", "ms", "pr", "rs", "sc", "pe", "ce", "ma", 
    "es", "am", "rn", "pb", "al", "se", "pi", "to", "ro", "ac", "rr", "ap", "df",
    "são paulo", "minas gerais", "rio de janeiro", "paraná", "rio grande do sul",
    "belo horizonte", "salvador", "recife", "fortaleza", "curitiba", "porto alegre", "vitória",
    "cuiabá", "goiânia", "belém", "manaus", "florianópolis",
    
    # Portugal (Distritos e Regiões)
    "lisboa", "lisbon", "porto", "braga", "aveiro", "coimbra", "setúbal", "leiria", 
    "faro", "viseu", "santarém", "viana do castelo", "vila real", "castelo branco", 
    "guarda", "évora", "beja", "bragança", "portalegre", "madeira", "açores", "azores",
    
    # Espanha (Comunidades Autônomas e Províncias)
    "madrid", "catalunya", "cataluña", "barcelona", "andalucía", "sevilla", "valencia", 
    "galicia", "a coruña", "basque country", "país vasco", "bilbao", "aragon", "zaragoza", 
    "castilla y león", "castilla-la mancha", "extremadura", "asturias", "oviedo", 
    "murcia", "navarra", "cantabria", "la rioja", "canarias", "baleares"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_sent_jobs():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_jobs(sent_jobs):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for link in sorted(sent_jobs):
            f.write(f"{link}\n")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Erro: TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não definidos!")
        return

    chat_id = str(TELEGRAM_CHAT_ID).strip()
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": False
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Erro ao enviar para Telegram ({response.status_code}): {response.text}")

def is_strictly_allowed_location(job_loc):
    """Retorna True SOMENTE para Brasil, Portugal ou Espanha."""
    loc_lower = job_loc.lower().strip()
    if not loc_lower:
        return False
        
    return any(region in loc_lower for region in ALLOWED_REGIONS)

def get_job_description(job_link):
    try:
        time.sleep(1.2)
        res = requests.get(job_link, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            desc_tag = soup.find("div", class_="show-more-less-html__markup") or soup.find("section", class_="description")
            if desc_tag:
                return desc_tag.text.lower()
    except Exception as e:
        print(f"Erro ao obter descrição: {e}")
    return ""

def is_valid_dam_job(title, link):
    """Aplica o filtro rigoroso para garantir que a vaga trata do assunto solicitado."""
    title_lower = title.lower()

    # 1. Se o título tiver QUALQUER termo de Segurança do Trabalho/TI/Outros, ELIMINA
    if any(ex in title_lower for ex in STRICT_EXCLUDE_TERMS):
        return False

    # 2. Verifica se BARRAGEM/PRESA e o ESCOPO (Segurança/Obra/Construção) estão no TÍTULO
    has_dam_in_title = any(dam in title_lower for dam in MANDATORY_DAM_TERMS)
    has_scope_in_title = any(scope in title_lower for scope in MANDATORY_SCOPE_TERMS)

    if has_dam_in_title and has_scope_in_title:
        return True

    # 3. Se não validar pelo título, analisa a DESCRIÇÃO completa
    desc = get_job_description(link)
    
    # Se a descrição indicar segurança do trabalho/patrimonial/TI, descarta
    if any(ex in desc for ex in ["segurança do trabalho", "segurança laboral", "segurança da informação", "segurança patrimonial"]):
        return False

    has_dam_in_desc = any(dam in desc for dam in MANDATORY_DAM_TERMS)
    has_scope_in_desc = any(scope in desc for scope in MANDATORY_SCOPE_TERMS)

    return has_dam_in_desc and has_scope_in_desc

def search_linkedin_jobs(keyword, location, sent_jobs):
    jobs = []

    for start in [0, 25]:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&f_TPR=r5184000&start={start}"
        
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("li")
        
        if not job_cards:
            break

        for card in job_cards:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            location_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")
            
            if title_tag and link_tag:
                link = link_tag["href"].split("?")[0]

                if link in sent_jobs:
                    continue

                title = title_tag.text.strip()
                company = company_tag.text.strip() if company_tag else "Empresa não informada"
                job_loc = location_tag.text.strip() if location_tag else ""

                # Trava Geográfica Absoluta
                if not is_strictly_allowed_location(job_loc):
                    continue

                # Trava de Conteúdo Estrita
                if not is_valid_dam_job(title, link):
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job_loc,
                    "link": link
                })
                
    return jobs

def main():
    sent_jobs = load_sent_jobs()
    found_jobs = []
    seen_in_this_run = set()

    for loc in ["Brasil", "Portugal", "Espanha"]:
        for kw in KEYWORDS:
            jobs = search_linkedin_jobs(kw, loc, sent_jobs)
            for job in jobs:
                if job["link"] not in seen_in_this_run:
                    seen_in_this_run.add(job["link"])
                    found_jobs.append(job)

    if not found_jobs:
        no_jobs_msg = (
            "🔍 **Nenhuma nova vaga encontrada** para as palavras-chave especificadas (Brasil, Portugal e Espanha).\n\n"
            "💬 *Mensagem do Dia:*\n"
            "Assim como uma grande estrutura requer fundações sólidas e tempo para se consolidar, "
            "as melhores oportunidades profissionais também exigem constância e paciência. "
            "A ausência de vagas no momento não significa falta de espaço, mas sim que o momento certo está sendo preparado. "
            "Mantenha o foco, continue se aprimorando e esteja pronto para quando a oportunidade surgir! 🏗️⚙️"
        )
        send_telegram_message(no_jobs_msg)
        return

    send_telegram_message(f"🚨 Novas Vagas Encontradas ({len(found_jobs)}):")

    for job in found_jobs[:20]:
        msg = f"📌 {job['title']}\n🏢 {job['company']}\n📍 {job['location']}\n🔗 {job['link']}"
        send_telegram_message(msg)
        sent_jobs.add(job['link'])

    save_sent_jobs(sent_jobs)

if __name__ == "__main__":
    main()
