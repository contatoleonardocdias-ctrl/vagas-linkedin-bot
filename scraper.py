import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Termos de busca focados
KEYWORDS = [
    "Segurança de Barragens", 
    "Engenheiro Civil de Segurança de Barragens",
    "Seguridad de Presas"  # Termo em espanhol para Espanha
]

# Países para filtragem geográfica
LOCATIONS = ["Brasil", "Portugal", "Espanha"]

# Palavras-chave obrigatórias no título ou resumo para validação estrita
STRICT_TERMS = ["barragem", "barragens", "presa", "presas", "dam", "dams"]

def send_telegram_message(message):
    """Envia mensagem em texto simples garantindo compatibilidade de caracteres."""
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

def search_linkedin_jobs(keyword, location):
    """Busca vagas públicas no LinkedIn filtradas por termo e localização."""
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
            company = company_tag.text.strip() if company_tag else "Empresa não informada"
            job_loc = location_tag.text.strip() if location_tag else location
            link = link_tag["href"].split("?")[0]
            
            # Filtro de Segurança: Garante que "barragem/presa" esteja no título ou na busca
            title_lower = title.lower()
            if any(term in title_lower for term in STRICT_TERMS) or "segurança" in title_lower or "seguridad" in title_lower:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job_loc,
                    "country": location,
                    "link": link
                })
            
    return jobs

def main():
    found_jobs = []
    seen_links = set()

    # Itera sobre cada país e cada palavra-chave
    for loc in LOCATIONS:
        for kw in KEYWORDS:
            jobs = search_linkedin_jobs(kw, loc)
            for job in jobs:
                if job["link"] not in seen_links:
                    seen_links.add(job["link"])
                    found_jobs.append(job)

    if not found_jobs:
        print("Nenhuma nova vaga de Segurança de Barragens encontrada nas últimas 24h.")
        return

    # Notificação do cabeçalho
    send_telegram_message(f"🚨 Novas Vagas: Segurança de Barragens (BR / PT / ES) - Total: {len(found_jobs)}")

    # Envio das vagas encontradas
    for job in found_jobs[:12]:
        msg = f"📌 {job['title']}\n🏢 {job['company']}\n📍 {job['location']}\n🔗 {job['link']}"
        send_telegram_message(msg)

if __name__ == "__main__":
    main()
