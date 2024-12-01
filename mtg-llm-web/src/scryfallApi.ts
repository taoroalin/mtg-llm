const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

interface CacheEntry {
  data: {
    cmc: number;
    image_uris: {
      normal: string;
    };
  };
  timestamp: number;
}

const cardCache = new Map<string, CacheEntry>();

export async function getCardByName(cardName: string) {
  const cached = cardCache.get(cardName);
  const now = Date.now();
  
  if (cached && now - cached.timestamp < CACHE_DURATION) {
    return cached.data;
  }

  const response = await fetch(
    `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(cardName)}`
  );
  const data = await response.json();
  
  cardCache.set(cardName, { data, timestamp: now });
  return data;
}