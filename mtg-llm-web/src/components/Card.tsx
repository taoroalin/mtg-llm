import styled from '@emotion/styled';
import { useState, useEffect } from 'react';
import { getCardByName, getPreferredPrinting } from '../scryfallApi';
import { BattlefieldCard } from '../types';

const CardContainer = styled.div<{
  tapped: boolean;
  isFallback: boolean;
  enteredThisTurn: boolean;
}>`
  width: 150px;
  height: 209px;
  ${({ isFallback }) =>
    isFallback &&
    `
    border: 2px solid #000;
    background: #f8f8f8;
    padding: 8px;
  `}
  border-radius: 10px;
  margin: 0;
  display: flex;
  flex-direction: column;
  transform-origin: center center;
  transform: ${({ tapped }) => (tapped ? 'rotate(90deg) translateY(-25px)' : 'none')};
  transition: transform 0.2s;
  filter: ${({ enteredThisTurn }) => (enteredThisTurn ? 'grayscale(50%)' : 'none')};
  position: relative;
`;

const Counters = styled.div`
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(255, 255, 255, 0.8);
  padding: 2px 4px;
  border-radius: 4px;
`;

const Counter = styled.div`
  font-size: 12px;
  color: #000;
`;

const CardName = styled.div`
  font-weight: bold;
  margin-bottom: 0px;
`;

const CardImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
`;

interface CardProps {
  name: string;
  battlefield_card?: BattlefieldCard;
}

export const Card = ({ name, battlefield_card }: CardProps) => {
  const [imageUrl, setImageUrl] = useState<string>();
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    const fetchCardImage = async () => {
      try {
        const imageUrl = await getPreferredPrinting(name);
        setImageUrl(imageUrl);
      } catch (error) {
        setImageError(true);
      }
    };
    fetchCardImage();
  }, [name]);

  const isEnteredThisTurn = battlefield_card?.entered_battlefield_this_turn ?? false;
  const counters = battlefield_card?.counters ?? {};

  return (
    <CardContainer
      tapped={battlefield_card?.tapped ?? false}
      isFallback={imageError}
      enteredThisTurn={isEnteredThisTurn}
    >
      {imageUrl ? (
        <CardImage src={imageUrl} onError={() => setImageError(true)} />
      ) : (
        <div>
          <CardName>{name}</CardName>
        </div>
      )}
      {Object.keys(counters).length > 0 && (
        <Counters>
          {Object.entries(counters).map(([type, count]) => (
            <Counter key={type}>
              {type}: {count}
            </Counter>
          ))}
        </Counters>
      )}
    </CardContainer>
  );
};