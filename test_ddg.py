from duckduckgo_search import DDGS
import json

def test():
    print("Testing DDGS...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text("python programming", max_results=5))
            print(f"Found {len(results)} results")
            print(json.dumps(results[:2], indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
