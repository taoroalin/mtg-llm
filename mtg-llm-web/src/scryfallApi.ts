import taoPreferredArtPrintings from './tao_preferred_art_printings.json';
type PreferredArtPrinting = {
  set: string;
  number: string;
}

type PreferredArtPrintings = {
  [cardName: string]: PreferredArtPrinting[];
}

const taoPreferredArtPrintingsTyped: PreferredArtPrintings = taoPreferredArtPrintings;

console.log({taoPreferredArtPrintings});
export function createCache<T extends (...args: any[]) => any>(fn: T) {
  const cache = new Map<string, Awaited<ReturnType<T>>>();
  return async (...args: Parameters<T>): Promise<Awaited<ReturnType<T>>> => {
    const key = JSON.stringify(args);
    if (!cache.has(key)) {
      cache.set(key, await fn(...args));
    }
    return cache.get(key)!;
  };
}

async function getCardByNameUncached(cardName: string) {
  const cardNamefixed = cardName.split('//')[0].trim();
    

  const response = await fetch(
    `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(cardNamefixed)}`
  );
  return await response.json() as {cmc: number, image_uris: {normal: string}};
}
export const getCardByName = createCache(getCardByNameUncached);

async function getCardBySetAndNumberUncached(set: string, number: string) {
  const response = await fetch(
    `https://api.scryfall.com/cards/${set.toLowerCase()}/${number}`
  );
  return await response.json() as {image_uris: {normal: string}};
}
export const getCardBySetAndNumber = createCache(getCardBySetAndNumberUncached);

interface Printing {
  set: string;
  image: string;
  collectorNumber: string;
  artist: string;
  isFullArt: boolean;
  hasFoil: boolean;
  language: string;
  price: number;
  flavor_name?: string;
}

async function getAllPrintsByNameUncached(cardName: string): Promise<Printing[]> {
    // For some reason non fullart query returns 0 full art printings for basic lands, need to search separately
  const cardNamefixed = cardName.split('//')[0].trim();
  const [fullart_response, normal_response] = await Promise.all([
    fetch(
      `https://api.scryfall.com/cards/search?q=!"${encodeURIComponent(cardNamefixed)}"+include:extras+is:fullart&unique=art&order=usd&dir=desc`
    ),
    fetch(
      `https://api.scryfall.com/cards/search?q=!"${encodeURIComponent(cardNamefixed)}"+include:extras&unique=art&order=usd&dir=desc`
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
    price: card.prices?.usd,
    flavor_name: card.flavor_name
  })).filter((p: Printing) => !p.flavor_name);
}
export const getAllPrintsByName = createCache(getAllPrintsByNameUncached);
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

async function getPreferredPrintingUncached(cardName: string) {
  if (taoPreferredArtPrintingsTyped[cardName]) {
    const printing = await getCardBySetAndNumber(taoPreferredArtPrintingsTyped[cardName][0].set, taoPreferredArtPrintingsTyped[cardName][0].number);
    return printing.image_uris.normal;
  }
  const printings = await getAllPrintsByName(cardName);
  const sorted = sortPrintingsByTaoPreference(printings);
  return sorted[0].image;
}
export const getPreferredPrinting = createCache(getPreferredPrintingUncached);
