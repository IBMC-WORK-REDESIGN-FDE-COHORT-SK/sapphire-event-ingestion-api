#!/usr/bin/env python3
"""
Script to ingest sample health metrics data into the API
Requires a valid JWT bearer token
"""

import json
import os
import sys
import time
from pathlib import Path
import requests
from typing import List, Dict

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
INGESTION_ENDPOINT = f"{API_BASE_URL}/v1/metrics/ingest"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

def get_bearer_token() -> str:
    """Get bearer token from environment or prompt user"""
    #token = os.getenv("BEARER_TOKEN")
    token = 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI1SjJtT2ZYU3A1ZndBdm40aVVkeGZ4V2xNOUI0R1pLVF9TUjNqM2ZzS3M0In0.eyJleHAiOjE3NzA0MDEzNjcsImlhdCI6MTc3MDQwMTA2NywianRpIjoiMmU3YjZhY2QtN2NiYy00NGUwLTgxNjEtMGI1M2Y5NTk3MmNkIiwiaXNzIjoiaHR0cDovL2xvY2FsaG9zdDo4MDkwL3JlYWxtcy9zYXBoaGlyZS11aSIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiIyYTMzMzc3ZC0yODg0LTQyZGMtOTExMC01M2VjZDE5ZTk1ZDMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJpbmdlc3Rpb24tYXBpIiwiYWNyIjoiMSIsImFsbG93ZWQtb3JpZ2lucyI6WyIvKiJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsib2ZmbGluZV9hY2Nlc3MiLCJkZWZhdWx0LXJvbGVzLXNhcGhoaXJlLXVpIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6ImVtYWlsIHByb2ZpbGUiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImNsaWVudEhvc3QiOiIxMC44OS4xLjEiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJzZXJ2aWNlLWFjY291bnQtaW5nZXN0aW9uLWFwaSIsImNsaWVudEFkZHJlc3MiOiIxMC44OS4xLjEiLCJjbGllbnRfaWQiOiJpbmdlc3Rpb24tYXBpIn0.RWFlAETTl4_oHIEmGf4e7wllMPSAvvodmxoheHCfwiPPSjezvS9110HZWDlTPNCY1i5OiAmez-KlXH71-JiL5J242IbhzzuQaJ_raWgp4KE2w065mLVmYOB6k-jkoeVwD3t7W0ciQ7UWhCwJs72U5oBADVtH-9rLBD7lgTO8R851WL0ljLQA84lsQmbPT1Ks8AwwoZXCl7cFEPrkSqCjiRAYWH67u35G5aNaEqOEmedELFmXSAsIcsFA66Oy1cTTQ67n2Krz0Hoxta790sx_-3B1SHZx6Xndno_mF4xbVOrXKA3VOBl2goQxr0folbDcs9-PcbwyRksCC1zJrNGBBw'
    
    if not token:
        print_warning("BEARER_TOKEN environment variable not set")
        print_info("Please enter your JWT bearer token:")
        token = input("> ").strip()
        
        if not token:
            print_error("No token provided. Exiting.")
            sys.exit(1)
    
    return token

def find_sample_files() -> List[Dict[str, str]]:
    """Find all sample JSON files"""
    sample_dir = Path(__file__).parent.parent / "sample_data"
    
    if not sample_dir.exists():
        print_error(f"Sample data directory not found: {sample_dir}")
        print_info("Please run 'python scripts/generate_sample_data.py' first")
        sys.exit(1)
    
    files = []
    for user_dir in sample_dir.iterdir():
        if user_dir.is_dir():
            for json_file in user_dir.glob("*.json"):
                files.append({
                    "user": user_dir.name,
                    "metric_type": json_file.stem,
                    "path": json_file
                })
    
    return sorted(files, key=lambda x: (x["user"], x["metric_type"]))

def ingest_file(file_info: Dict, token: str, delay: float = 0.5) -> Dict:
    """
    Ingest a single JSON file
    
    Args:
        file_info: File information dict
        token: Bearer token
        delay: Delay between requests in seconds
        
    Returns:
        Dict with result information
    """
    try:
        # Read JSON file
        with open(file_info["path"], "r") as f:
            payload = json.load(f)
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Send request
        response = requests.post(
            INGESTION_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Add delay to avoid overwhelming the API
        time.sleep(delay)
        
        # Parse response
        if response.status_code in [200, 202]:
            result = response.json()
            return {
                "success": True,
                "status_code": response.status_code,
                "accepted": result.get("accepted_count", 0),
                "rejected": result.get("rejected_count", 0),
                "request_id": result.get("request_id", "N/A")
            }
        else:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_detail = error_data["error"].get("message", str(error_data))
                else:
                    error_detail = str(error_data)
            except:
                error_detail = response.text[:200]
            
            # Log full error response for debugging
            import sys
            print(f"\n{Colors.RED}ERROR Response Body:{Colors.RESET}", file=sys.stderr)
            print(f"{Colors.RED}{response.text}{Colors.RESET}\n", file=sys.stderr)
            
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_detail
            }
    
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout (30s)"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Connection error - Is the API running at {API_BASE_URL}?"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Main ingestion process"""
    print_header("Health Metrics Data Ingestion Tool")
    
    # Configuration
    print_info(f"API Endpoint: {INGESTION_ENDPOINT}")
    
    # Get bearer token
    token = get_bearer_token()
    print_success("Bearer token loaded")
    
    # Find sample files
    print_info("Scanning for sample data files...")
    files = find_sample_files()
    
    if not files:
        print_error("No sample data files found")
        sys.exit(1)
    
    print_success(f"Found {len(files)} files to ingest")
    
    # Group by user
    users = {}
    for file_info in files:
        user = file_info["user"]
        if user not in users:
            users[user] = []
        users[user].append(file_info)
    
    print_info(f"Data for {len(users)} users: {', '.join(users.keys())}")
    
    # Confirm before proceeding
    print(f"\n{Colors.YELLOW}Ready to ingest {len(files)} files. Continue? (y/n): {Colors.RESET}", end="")
    confirm = input().strip().lower()
    
    if confirm != 'y':
        print_warning("Ingestion cancelled")
        sys.exit(0)
    
    # Ingest files
    print_header("Ingesting Data")
    
    total_success = 0
    total_failed = 0
    total_accepted = 0
    total_rejected = 0
    
    for user, user_files in users.items():
        print(f"\n{Colors.BOLD}User: {user}{Colors.RESET}")
        print("-" * 70)
        
        for file_info in user_files:
            metric_type = file_info["metric_type"]
            print(f"  Ingesting {metric_type}...", end=" ", flush=True)
            
            result = ingest_file(file_info, token)
            
            if result["success"]:
                print_success(f"OK (accepted: {result['accepted']}, rejected: {result['rejected']})")
                total_success += 1
                total_accepted += result["accepted"]
                total_rejected += result["rejected"]
            else:
                print_error(f"FAILED")
                print(f"    Error: {result.get('error', 'Unknown error')}")
                if "status_code" in result:
                    print(f"    Status: {result['status_code']}")
                total_failed += 1
    
    # Summary
    print_header("Ingestion Summary")
    
    print(f"Files processed:     {len(files)}")
    print(f"  {Colors.GREEN}✓ Successful:      {total_success}{Colors.RESET}")
    print(f"  {Colors.RED}✗ Failed:          {total_failed}{Colors.RESET}")
    print(f"\nMetrics:")
    print(f"  {Colors.GREEN}✓ Accepted:        {total_accepted}{Colors.RESET}")
    print(f"  {Colors.RED}✗ Rejected:        {total_rejected}{Colors.RESET}")
    
    if total_failed > 0:
        print(f"\n{Colors.YELLOW}⚠ Some files failed to ingest. Check the errors above.{Colors.RESET}")
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}✓ All data ingested successfully!{Colors.RESET}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.RESET}")
        print(f"  1. Check Kafka UI: http://localhost:8080")
        print(f"  2. View topics: health.metrics.*")
        print(f"  3. Verify messages are properly deserialized with Avro schemas")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠ Ingestion interrupted by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}✗ Unexpected error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
