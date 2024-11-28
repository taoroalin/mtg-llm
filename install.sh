mkdir assets
cd assets
[ ! -f AtomicCards.json ] && wget https://mtgjson.com/api/v5/AtomicCards.json
[ ! -f MagicCompRules.txt ] && wget https://media.wizards.com/2024/downloads/MagicCompRules%2020241108.txt -O MagicCompRules.txt
mkdir example_decks_raw
cd example_decks_raw
for deck in Cats Elves Goblins Healing Inferno Pirates; do
    wget "https://mtgjson.com/api/v5/decks/${deck}_FDN.json" -O "${deck}_FDN.json"
done
cd ..
cd ..
python process_assets.py
