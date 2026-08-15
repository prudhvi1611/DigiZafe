import asyncio
import time
import httpx

API_BASE_URL = "http://localhost:8000/api/v1"
CONCURRENCY = 10
REQUESTS_PER_ENDPOINT = 50

async def measure_endpoint(client, name, method, url, data=None):
    latencies = []
    errors = 0
    
    async def make_request():
        nonlocal errors
        start_time = time.perf_counter()
        try:
            if method == 'GET':
                resp = await client.get(url)
            else:
                resp = await client.post(url, json=data)
            resp.raise_for_status()
        except Exception as e:
            errors += 1
        finally:
            end_time = time.perf_counter()
            latencies.append(end_time - start_time)
            
    tasks = [make_request() for _ in range(REQUESTS_PER_ENDPOINT)]
    await asyncio.gather(*tasks)
    
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    
    print(f"{name:30} | {REQUESTS_PER_ENDPOINT:4} reqs | p50: {p50*1000:6.1f}ms | p95: {p95*1000:6.1f}ms | errors: {errors}")

async def run_baseline():
    print(f"=== DigiZafe Performance Baseline (Concurrency: {CONCURRENCY}) ===")
    print(f"{'Endpoint':30} | Reqs | p50 (ms) | p95 (ms) | Errors")
    print("-" * 75)
    
    async with httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=CONCURRENCY)) as client:
        # Wait for API
        try:
            await client.get(f"{API_BASE_URL}/health")
        except:
            print("API not reachable!")
            return
            
        await measure_endpoint(client, "Health", 'GET', f"{API_BASE_URL}/health")
        await measure_endpoint(client, "Identity Anchors (List)", 'GET', f"{API_BASE_URL}/identity/anchors?limit=10")
        
if __name__ == "__main__":
    asyncio.run(run_baseline())
