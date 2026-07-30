import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Termos de busca exatos
KEYWORDS = [
    '"Segurança de Barragens"', 
    '"Engenheiro Civil de Segurança de Barragens"',
    '"Seguridad de Presas"'
]

LOCATIONS = ["Brasil", "Portugal", "Espanha"]

# Estados do Brasil, Distritos de Portugal e Comunidades Autônomas/Regiões da Espanha
ALLOWED_REGIONS = [
    # Países
    "brasil", "brazil", "portugal", "espanha", "spain", "españa",
    
    # Brasil (Siglas e Nomes)
    "sp", "mg", "rj", "pa", "ba", "go", "mt", "ms", "pr", "rs", "sc", "pe", "ce", "ma", 
    "es", "am", "rn", "pb", "al", "se", "pi", "to", "ro", "ac", "rr", "ap", "df",
    "são paulo", "minas gerais", "rio de janeiro", "paraná", "rio grande do sul",
    
    # Portugal (Distritos e Regiões)
    "lisboa", "lisbon", "porto", "braga", "aveiro", "coimbra", "setúbal", "leiria", 
    "faro", "viseu", "santarém", "viana do castelo", "vila real", "castelo branco", 
    "guarda", "évora", "beja", "bragança", "portalegre", "madeira", "açores", "azores",
    
    # Espanha (Comunidades Autônomas e Províncias Principais)
    "madrid", "catalunya", "cataluña", "barcelona", "andalucía", "sevilla", "valencia", 
    "galicia", "a coruña", "basque country", "país vasco", "bilbao", "aragon", "zaragoza", 
    "castilla y león", "castilla-la mancha", "extremadura", "asturias", "oviedo", 
    "murcia", "navarra", "cantabria", "la rioja", "canarias", "baleares"
]

# Palavras de Segurança de Barragens (Pelo menos uma DEVE existir no título)
DAM_TERMS = ["barragem", "barragens", "presa", "presas", "dam", "dams"]

# Lista Negra de Títulos (elimina Segurança do Trabalho, TI, etc.)
EXCLUDE_TERMS = [
    "trabalho", "laboral", "ocupacional", "hst", "sst",
    "patrimonial", "informação", "informacao", "ti", "dados", "cyber",
    "física", "fisica", "corporativa", "veicular", "privacidade"
]

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Erro: TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não definidos nos Secrets!")
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

def is_allowed_location(job_loc):
    """Verifica se a localização pertence ao Brasil, Portugal ou Espanha."""
    loc_lower = job_loc.lower()
    
    blocked_locs = ["united states", "estados unidos", "usa", "canada", "mexico", "colombia", "chile", "united kingdom", "uk"]
    if any(b in loc_lower for b in blocked_locs):
        return False
        
    return any(region in loc_lower for region in ALLOWED_REGIONS)

def search_linkedin_jobs(keyword, location):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&f_TPR=r86400"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Erro na busca do LinkedIn para '{keyword}' em '{location}': Status {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    
    job_cards = soup.find_all("li")
    for card in job_cards:
        title_tag = card.find("h3", class_="base-search-card__title")
        company_tag = card.find("h4", class_="base-search-card__subtitle")
        location_tag = card.find("span", class_="job-search-card__location")
        link_tag = card.find("a", class_="base-card__full-link")
        
        if title_tag and link_tag:
            title = title_tag.text.strip()
            title_lower = title.lower()
            company = company_tag.text.strip() if company_tag else "Empresa não informada"
            job_loc = location_tag.text.strip() if location_tag else location
            link = link_tag["href"].split("?")[0]
            
            # Filtro 1: Validação de localização estrita (BR, PT, ES)
            if not is_allowed_location(job_loc):
                continue

            # Filtro 2: Exclui palavras de segurança do trabalho / TI
            has_excluded_term = any(ex in title_lower for ex in EXCLUDE_TERMS)
            
            # Filtro 3: Deve conter obrigatoriamente termo de barragem/presa
            has_dam_term = any(dam in title_lower for dam in DAM_TERMS)
            
            if has_dam_term and not has_excluded_term:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job_loc,
                    "link": link
                })
            
    return jobs

def main():
    found_jobs = []
    seen_links = set()

    for loc in LOCATIONS:
        for kw in KEYWORDS:
            jobs = search_linkedin_jobs(kw, loc)
            for job in jobs:
                if job["link"] not in seen_links:
                    seen_links.add(job["link"])
                    found_jobs.append(job)

    # Caso NÃO encontre vagas
    if not found_jobs:
        no_jobs_msg = (
            "🔍 **Nenhuma nova vaga encontrada nas últimas 24h** (Brasil, Portugal e Espanha).\n\n"
            "💬 *Mensagem do Dia:*\n"
            "Assim como uma grande estrutura requer fundações sólidas e tempo para se consolidar, "
            "as melhores oportunidades profissionais também exigem constância e paciência. "
            "A ausência de vagas hoje não significa falta de espaço, mas sim que o momento certo está sendo preparado. "
            "Mantenha o foco, continue se aprimorando e esteja pronto para quando a oportunidade surgir! 🏗️⚙️"
        )
        send_telegram_message(no_jobs_msg)
        return

    # Notificação quando ENCONTRAR vagas
    send_telegram_message(f"🚨 Novas Vagas Exclusivas (BR/PT/ES): Segurança de Barragens ({len(found_jobs)})")

    for job in found_jobs[:10]:
        msg = f"📌 {job['title']}\n🏢 {job['company']}\n📍 {job['location']}\n🔗 {job['link']}"
        send_telegram_message(msg)

if __name__ == "__main__":
    main()
