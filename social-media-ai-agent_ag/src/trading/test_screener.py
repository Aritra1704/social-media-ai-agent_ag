import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from trading.screener import AIScreener

def test_screener():
    screener = AIScreener()
    screening_criteria = 'high market cap'
    results = screener.run(screening_criteria)
    print(results)

if __name__ == "__main__":
    test_screener()