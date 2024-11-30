import styled from '@emotion/styled';

const CardContainer = styled.div<{ tapped: boolean }>`
  width: 150px;
  height: 209px; // Standard MTG card ratio
  border: 2px solid #000;
  border-radius: 10px;
  padding: 8px;
  margin: 8px;
  background: #f8f8f8;
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

export const Card = ({ name, tapped, power, toughness, damage = 0 }: CardProps) => (
  <CardContainer tapped={tapped}>
    <CardName>{name}</CardName>
    {power !== undefined && toughness !== undefined && (
      <CardStats>
        {power}/{toughness} {damage > 0 && `(${damage} damage)`}
      </CardStats>
    )}
  </CardContainer>
);