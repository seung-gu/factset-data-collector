"""Step 6: Generate and upload P/E ratio plot, and purge Camo cache."""

import os
import re
import time
import urllib.request
import json
import tempfile
from pathlib import Path

from src.factset_report_analyzer.utils.plot import plot_pe_ratio_with_price
from src.factset_report_analyzer.utils.cloudflare import upload_file_to_public_cloud


def generate_pe_ratio_plot() -> None:
    """Generate P/E ratio plot, upload to public bucket, and purge Camo cache."""
    print("-" * 80)
    print(" 📊 Step 6: Generating P/E ratio plot...")
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plot_path = tmp_path / "pe_ratio_plot.png"
            plot_pe_ratio_with_price(output_path=plot_path)
            
            # Upload to public bucket
            if upload_file_to_public_cloud(plot_path, "pe_ratio_plot.png"):
                print("✅ Uploaded pe_ratio_plot.png to public bucket")
                _purge_camo_cache()
            else:
                print("⚠️  Failed to upload pe_ratio_plot.png")
    except Exception as e:
        print(f"⚠️  Could not generate P/E ratio plot: {e}")
        import traceback
        traceback.print_exc()


def _purge_camo_cache() -> None:
    """Purge Camo cache to force GitHub to show updated image."""
    try:
        time.sleep(10)  # Wait for GitHub to render README
        repo = os.getenv('GITHUB_REPOSITORY', 'seung-gu/factset-report-analyzer')
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/readme",
            headers={"Accept": "application/vnd.github.html"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8')
        
        # Find and purge Camo URLs for pe_ratio_plot
        # Camo URL structure: https://camo.githubusercontent.com/{hash}/{hex_encoded_url}
        camo_matches = re.findall(r'https://camo\.githubusercontent\.com/([^/]+)/([^"\s<>]+)', html)
        pe_urls = []
        for hash_part, encoded_url in camo_matches:
            try:
                decoded = bytes.fromhex(encoded_url).decode('utf-8')
                if 'pe_ratio_plot' in decoded:
                    pe_urls.append(f'https://camo.githubusercontent.com/{hash_part}/{encoded_url}')
            except:
                pass
        
        for url in set(pe_urls):  # Remove duplicates
            try:
                purge_req = urllib.request.Request(url, method='PURGE', headers={'User-Agent': 'GitHub-Actions'})
                with urllib.request.urlopen(purge_req, timeout=10) as purge_resp:
                    if json.loads(purge_resp.read().decode('utf-8')).get('status') == 'ok':
                        print(f"✅ Purged Camo cache")
            except:
                pass
    except Exception as e:
        print(f"⚠️  Could not purge Camo cache: {e}")

