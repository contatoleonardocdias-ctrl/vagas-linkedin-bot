import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

KEYWORDS = [
    "Segurança de Barragens", 
    "Engenheiro Civil de Segurança de Barragens"
]
LOCATION = "Brasil"

def send_telegram_message(message):
    """Envia mensagem em texto puro para evitar erros de parse do Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")

def search_linkedin_jobs(keyword):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={LOCATION}&f_TPR=r86400"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao buscar vagas para '{keyword}': Status {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    
    job_cards = soup.find_all("li")
    for card in job_cards:
        title_tag = card.find("h3", class_="base-search-card__title")
        company_tag = card.find("h4", class_="base-search-card__subtitle")
        link_tag = card.find("a", class_="base-card__full-link")
        
        if title_tag and link_tag:
            title = title_tag.text.strip()
            company = company_tag.text.strip() if company_tag else "Empresa não informada"
            link = link_tag["href"].split("?")[0]
            
            jobs.append({
                "title": title,
                "company": company,
                "link": link
            })
            
    return jobs

def main():
    found_jobs = []
    seen_links = set()

    for kw in KEYWORDS:
        jobs = search_linkedin_jobs(kw)
        for job in jobs:
            if job["link"] not in seen_links:
                seen_links.add(job["link"])
                found_jobs.append(job)

    if not found_jobs:
        print("Nenhuma nova vaga encontrada nas últimas 24h.")
        return

    # Notifica o cabeçalho
    header = f"🚨 Novas Vagas: Segurança de Barragens ({len(found_jobs)})\n"
    send_telegram_message(header)

    # Envia cada vaga individualmente
    for job in found_jobs[:10]:
        msg = f"📌 {job['title']}\n🏢 {job['company']}\n🔗 {job['link']}"
        send_telegram_message(msg)

if __name__ == "__main__":
    main()
