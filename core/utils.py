import time
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .models import Testimonial

def scrape_data_in_thread(target_url, css_selector):
    """
    Scrapes Text, Name, AND Title. No longer takes screenshots.
    """
    scraped_items = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 2000}) 
        
        try:
            print(f"--- Scraping {target_url} ---")
            page.goto(target_url, timeout=60000)
            
            # Scroll to ensure elements load
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1)

            elements = page.query_selector_all(css_selector)
            print(f"Found {len(elements)} cards.")
            
            for i, element in enumerate(elements):
                try:
                    # 1. Pinned Check
                    class_attr = element.get_attribute("class") or ""
                    is_pinned = "pinned-card" in class_attr
                    
                    # 2. Expand Logic (Click 'Read More')
                    if not is_pinned:
                        expand_btn = element.query_selector('.chevron-down')
                        if expand_btn and expand_btn.is_visible():
                            element.scroll_into_view_if_needed()
                            expand_btn.click()
                            time.sleep(0.3) 
                    
                    # 3. Parse HTML
                    html_content = element.inner_html()
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # --- NEW: EXTRACT TITLE ---
                    # Look for card-title (standard) or pinned-card-title
                    title_node = soup.find(class_='card-title')
                    if not title_node:
                        title_node = soup.find(class_='pinned-card-title')
                    
                    review_title = title_node.get_text(strip=True) if title_node else ""

                    # --- EXTRACT TEXT ---
                    content_node = soup.find(class_='content-full')
                    if not content_node:
                        content_node = soup.find(class_='pinned-card-full')

                    if content_node:
                        review_text = content_node.get_text(separator="\n", strip=True)
                    else:
                        text_candidates = soup.find_all(['p', 'div', 'span'])
                        valid_texts = [t.get_text(strip=True) for t in text_candidates if len(t.get_text(strip=True)) > 15]
                        review_text = max(valid_texts, key=len) if valid_texts else ""

                    # --- EXTRACT NAME ---
                    author_node = soup.find(class_='card-author')
                    if not author_node:
                        author_node = soup.find(class_='pinned-card-author')
                    
                    client_name = author_node.get_text(strip=True) if author_node else f"Client #{i+1}"

                    # Add to list (Note: No screenshot_bytes anymore)
                    scraped_items.append({
                        'title': review_title,
                        'client_name': client_name,
                        'review_text': review_text,
                        'is_featured': is_pinned,
                    })
                    print(f"   + Scraped: {review_title} - {client_name}")
                    
                except Exception as e:
                    print(f"   - Error scraping item #{i}: {e}")

        except Exception as e:
            print(f"Global Scrape Error: {e}")
        finally:
            browser.close()
            
    return scraped_items

def scrape_and_save_testimonials(agent, target_url, css_selector=".card"):
    # 1. Run Scraper
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(scrape_data_in_thread, target_url, css_selector)
        scraped_data = future.result()

    # 2. Save to DB
    print(f"--- Saving {len(scraped_data)} items to DB ---")
    saved_count = 0
    
    for item in scraped_data:
        try:
            # Skip empty reviews
            if not item['review_text']:
                continue

            testimonial = Testimonial(
                agent=agent,
                title=item['title'][:200], # Save the title
                client_name=item['client_name'][:100],
                review_text=item['review_text'],
                is_featured=item['is_featured']
                # No screenshot saving here anymore
            )
            testimonial.save()
            saved_count += 1
            
        except Exception as e:
            print(f"DB Save Error: {e}")

    return saved_count