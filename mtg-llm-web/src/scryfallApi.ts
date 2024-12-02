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
    // For some reason non fullart query returns 0 full art printings for basic lands, need to search separately
  const [fullart_response, normal_response] = await Promise.all([
    fetch(
      `https://api.scryfall.com/cards/search?q=!"${encodeURIComponent(cardName)}"+include:extras+is:fullart&unique=art&order=usd&dir=desc`
    ),
    fetch(
      `https://api.scryfall.com/cards/search?q=!"${encodeURIComponent(cardName)}"+include:extras&unique=art&order=usd&dir=desc`
    )
  ]);
  const [fullart_data, normal_data] = await Promise.all([fullart_response.json(), normal_response.json()]);
  const data = fullart_response.status === 404 || fullart_data.data.length === 0 ? normal_data.data : fullart_data.data;
    
  return data.map((card: any) => ({
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
    const getPreferenceScore = (printing: Printing) => {
      const artistIndex = preferredArtists.indexOf(printing.artist) === -10 ? -1 : preferredArtists.indexOf(printing.artist);
      return artistIndex + (printing.isFullArt ? 20 : 0) + (printing.language === "en" ? 20 : 0) + (printing.price ?? 0);
    }
    
    const aNum = getPreferenceScore(a);
    const bNum = getPreferenceScore(b);
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