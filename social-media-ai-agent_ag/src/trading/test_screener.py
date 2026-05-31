import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print("Added path:", sys.path[0])

from trading.screener import AIScreener

def test_screener():
    screener = AIScreener()
    screening_criteria = "stocks with high market capitalization and good growth prospects"
    filtered_instruments = screener.run(screening_criteria)
    print("Filtered Instruments:", filtered_instruments)

if __name__ == "__main__":
    test_screener()