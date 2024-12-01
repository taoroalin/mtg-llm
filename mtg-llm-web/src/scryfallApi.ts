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

interface Printing {
  set: string;
  image: string;
  collectorNumber: string;
  artist: string;
  isFullArt: boolean;
  hasFoil: boolean;
  language: string;
  price: number;
}

export async function getAllPrintsByName(cardName: string): Promise<Printing[]> {
  const response = await fetch(
    `https://api.scryfall.com/cards/search?q=!"${encodeURIComponent(cardName)}"+include:extras+prefer:newest`
  );
  const data = await response.json();
  return data.data.map((card: any) => ({
    set: card.set_name,
    image: card.image_uris?.normal,
    collectorNumber: card.collector_number,
    artist: card.artist,
    isFullArt: card.full_art,
    hasFoil: card.foil,
    language: card.lang,
    price: card.prices?.usd
  }));
}

export function sortPrintingsByTaoPreference(printings: Printing[]) {
  const preferredArtists = [
    "Richard Kane Ferguson",
    "Kev Walker",
    "Johannes Voss",
    "Chris Rahn",
    "Raymond Swanland",
    "Magali Villeneuve",
    "Volkan Baga",
    "Ron Spencer",
    "Wayne Reynolds",
    "Mark Tedin",
    "Christopher Rush",
    "Terese Nielsen",
    "Rebecca Guay",
    "Seb McKinnon"
  ];

  return printings.sort((a, b) => {
    const aIndex = preferredArtists.indexOf(a.artist) === -1 ? -1 : preferredArtists.indexOf(a.artist);
    const bIndex = preferredArtists.indexOf(b.artist) === -1 ? -1 : preferredArtists.indexOf(b.artist);
    
    const aNum = aIndex+(a.isFullArt?20:0)+(a.language === "en" ? 20 : 0)+(a.price ?? 0);
    const bNum = bIndex+(b.isFullArt?20:0)+(b.language === "en" ? 20 : 0)+(b.price ?? 0);
    const result =  bNum - aNum;
    // console.log({a, b, result});
    return result;
  });
}

export async function getPreferredPrinting(cardName: string) {
  const printings = await getAllPrintsByName(cardName);
//   if (cardName.match(/^(Plains|Island|Swamp|Mountain|Forest)$/)) {
//     console.log({"fullArt": printings.filter(p => p.isFullArt)[0]?.image});
//   }
  const sorted = sortPrintingsByTaoPreference(printings);
  return sorted[0].image;
}