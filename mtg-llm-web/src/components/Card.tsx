import styled from '@emotion/styled';
import { useState, useEffect } from 'react';

const CardContainer = styled.div<{ tapped: boolean, isFallback: boolean }>`
  width: 150px;
  height: 209px; // Standard MTG card ratio
  ${props => props.isFallback && `
    border: 2px solid #000;
    background: #f8f8f8;
    padding: 8px;
  `}
  border-radius: 10px;
  margin: 8px;
  display: flex;
  flex-direction: column;
  transform: ${props => props.tapped ? 'rotate(90deg)' : 'none'};
  transition: transform 0.2s;
`;

const CardName = styled.div`
  font-weight: bold;
  margin-bottom: 4px;
`;

const CardStats = styled.div`
  margin-top: auto;
`;

interface CardProps {
  name: string;
  tapped: boolean;
  power?: number | string;
  toughness?: number | string;
  damage?: number;
}

const CardImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
`;

const FallbackCard = styled(CardContainer)`
  background: #e0e0e0;
`;

interface CardProps {
  name: string;
  tapped: boolean;
  power?: number | string;
  toughness?: number | string;
  damage?: number;
}

export const Card = ({ name, tapped, power, toughness, damage = 0 }: CardProps) => {
  const [imageUrl, setImageUrl] = useState<string>();
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    const fetchCardImage = async () => {
      try {
        const response = await fetch(
          `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}`
        );
        const data = await response.json();
        setImageUrl(data.image_uris?.normal);
      } catch (error) {
        setImageError(true);
      }
    };
    fetchCardImage();
  }, [name]);

  if (imageUrl && !imageError) {
    return (
      <CardContainer tapped={tapped} isFallback={imageError}>
        <CardImage src={imageUrl} onError={() => setImageError(true)} />
      </CardContainer>
    );
  }

  return (
    <FallbackCard tapped={tapped} isFallback={true}>
      <CardName>{name}</CardName>
      {power !== undefined && toughness !== undefined && (
        <CardStats>
          {power}/{toughness} {damage > 0 && `(${damage} damage)`}
        </CardStats>
      )}
    </FallbackCard>
  );
};