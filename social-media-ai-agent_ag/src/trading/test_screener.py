from screener import AIScreener

def test_screener():
    screener = AIScreener()
    screening_criteria = 'high market cap'
    results = screener.run(screening_criteria)
    print(results)

if __name__ == "__main__":
    test_screener()