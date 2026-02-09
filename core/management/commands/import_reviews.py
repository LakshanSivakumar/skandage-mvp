import time
import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from core.models import Agent, Testimonial

class Command(BaseCommand):
    help = 'Scrapes reviews + screenshots from a website using a CSS selector'

    def add_arguments(self, parser):
        parser.add_argument('slug', type=str, help='The slug of the Agent (e.g., ryan-siow)')
        parser.add_argument('url', type=str, help='The external URL (e.g., https://ryansiow.producer.today/)')
        parser.add_argument('selector', type=str, help='The CSS class of the review card (e.g., .card)')

    def handle(self, *args, **options):
        agent_slug = options['slug']
        target_url = options['url']
        css_selector = options['selector']

        # 1. Get the Agent
        try:
            agent = Agent.objects.get(slug=agent_slug)
        except Agent.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Agent with slug '{agent_slug}' not found."))
            return

        self.stdout.write(self.style.WARNING(f"🚀 Launching browser to scrape: {target_url}"))
        self.stdout.write(f"   Looking for elements with class: {css_selector}")

        with sync_playwright() as p:
            # 2. Launch Headless Browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 3. Load Page
            page.goto(target_url, timeout=60000) # 60s timeout
            
            # Scroll to bottom to ensure lazy-loaded reviews appear
            self.stdout.write("   scrolling down to load images...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3) # Wait for animations/images

            # 4. Find Elements
            elements = page.query_selector_all(css_selector)
            count = len(elements)
            
            if count == 0:
                self.stdout.write(self.style.ERROR(f"❌ No elements found with selector '{css_selector}'. Check your spelling."))
                browser.close()
                return

            self.stdout.write(self.style.SUCCESS(f"✅ Found {count} potential reviews. Processing..."))

            # 5. Extract & Save
            imported_count = 0
            for i, element in enumerate(elements):
                try:
                    # --- A. Parse HTML for Text ---
                    html_content = element.inner_html()
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Heuristic 1: Find Client Name (look for bold text or headers)
                    name_candidates = soup.find_all(['h3', 'h4', 'h5', 'strong', 'b', 'h6'])
                    if name_candidates:
                        # Pick the one with reasonable length (not too long)
                        client_name = name_candidates[0].get_text().strip()
                    else:
                        client_name = f"Client Review #{i+1}"

                    # Heuristic 2: Find Review Body (longest paragraph/div)
                    text_candidates = soup.find_all(['p', 'div', 'span'])
                    # Filter out empty or very short strings
                    valid_texts = [t.get_text().strip() for t in text_candidates if len(t.get_text().strip()) > 10]
                    
                    if valid_texts:
                        # Assume the longest block of text is the review
                        review_text = max(valid_texts, key=len)
                    else:
                        review_text = "Review content captured in screenshot."

                    # Skip if it looks empty
                    if len(review_text) < 5:
                        continue

                    # --- B. Capture Screenshot ---
                    # We add some padding or white background if transparent
                    screenshot_bytes = element.screenshot()
                    
                    # --- C. Save to Database ---
                    testimonial = Testimonial(
                        agent=agent,
                        client_name=client_name[:100],
                        review_text=review_text,
                        is_featured=False # Safety: let user approve them first
                    )
                    
                    # Name the file
                    file_name = f"imported_{agent.slug}_{int(time.time())}_{i}.png"
                    testimonial.screenshot.save(file_name, ContentFile(screenshot_bytes))
                    testimonial.save()

                    self.stdout.write(f"   [{i+1}/{count}] Imported: {client_name}")
                    imported_count += 1

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Failed to capture #{i+1}: {e}"))

            browser.close()
            self.stdout.write(self.style.SUCCESS(f"\n🎉 DONE! Successfully imported {imported_count} testimonials."))