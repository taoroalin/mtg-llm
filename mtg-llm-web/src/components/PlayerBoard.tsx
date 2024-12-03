import styled from '@emotion/styled';
import { Card } from './Card';
import { PlayerBoard as PlayerBoardType } from '../types';
import { useState, useEffect } from 'react';
import { getCardByName } from '../scryfallApi';
import { BattlefieldCard } from '../types';
const CARD_WIDTH = 147;
const CARD_HEIGHT = 205;

const BoardContainer = styled.div`
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 14px;
  margin: 10px;
`;

const Zone = styled.div`
  margin: 10px 0;
`;

const Battlefield = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  min-height: ${CARD_HEIGHT}px;
`;
const Hand = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  min-height: ${CARD_HEIGHT}px;
  border: 2px solid rgba(0,0,0);
  border-radius: 8px;
  padding: 8px;
  background: rgba(200, 200, 200, 0.7);
`;

const CardWrapper = styled.div<{tapped: boolean}>`
  width: ${props => props.tapped ? CARD_HEIGHT : CARD_WIDTH}px;
  height: ${props => props.tapped ? CARD_WIDTH : CARD_HEIGHT}px;
  position: relative;
`;

interface PlayerBoardProps {
  board: PlayerBoardType;
  playerIndex: number;
  gameId: string;
}

export const PlayerBoard = ({ board, playerIndex, gameId }: PlayerBoardProps) => {
  const [sortedBattlefield, setSortedBattlefield] = useState<{card: BattlefieldCard, manaValue: number}[]>(Object.values(board.battlefield).map(card => ({card: card, manaValue: 0})));
  const [sortedHand, setSortedHand] = useState<{name: string, manaValue: number}[]>(board.hand.map(card => ({name: card, manaValue: 0})));

  useEffect(() => {
    const fetchAndSortCards = async () => {
      const battlefieldCards = await Promise.all(
        Object.values(board.battlefield).map(async card => {
          let manaValue;
          try {
            const cardData = await getCardByName(card.card);
            manaValue = cardData.cmc;
          } catch {
            manaValue = 100;
            console.error(`Error fetching card data for ${card.card}`);
          }
          return { card: card, manaValue };
        })
      );

      const handCards = await Promise.all(
        board.hand.map(async cardName => {
          const { cmc:manaValue } = await getCardByName(cardName);
          return { name: cardName, manaValue };
        })
      );

      setSortedBattlefield(battlefieldCards.sort((a, b) => 
        a.manaValue === b.manaValue ? 
          a.card.card.localeCompare(b.card.card) : 
          a.manaValue - b.manaValue
      ));
      setSortedHand(handCards.sort((a, b) => 
        a.manaValue === b.manaValue ? 
          a.name.localeCompare(b.name) : 
          a.manaValue - b.manaValue
      ));
    };

    fetchAndSortCards();
  }, [board]);

  return (
    <BoardContainer style={{
      backgroundImage: `url(http://localhost:8000/playmat/${gameId}/${playerIndex}.png)`,
    backgroundPosition: 'center',
    backgroundRepeat: 'repeat',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    backgroundBlendMode: 'overlay'
  }}>
    <h2 style={{marginTop: '4px', marginBottom: '4px', 'marginLeft':'0px'}}>Player {playerIndex} (Life: {board.life})</h2>
    
    <Zone>
      <div><strong>Battlefield</strong></div>
      <Battlefield>
        {sortedBattlefield.map(({card}) => (
          <CardWrapper key={card.battlefield_id} tapped={card.tapped}>
            <Card 
              name={card.card}
              tapped={card.tapped}
              damage={card.marked_damage}
            />
          </CardWrapper>
        ))}
      </Battlefield>
    </Zone>

    <Zone>
      <div><strong>Hand ({board.hand.length} cards)</strong></div>
      <Hand>
        {sortedHand.map((card, i) => (
          <CardWrapper key={i} tapped={false}>
            <Card name={card.name} tapped={false} />
          </CardWrapper>
        ))}
      </Hand>
    </Zone>
    </BoardContainer>
  );
};