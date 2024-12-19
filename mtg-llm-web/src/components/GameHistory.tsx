import styled from '@emotion/styled'
import { HistoryStep } from '../types'
import ReactMarkdown from 'react-markdown'

const ChatPanel = styled.div`
  padding: 4px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  max-height: 100%;
  box-sizing: border-box;
`

const ChatMessage = styled.div`
  margin-bottom: 10px;
  padding: 4px;
  background: white;
  border-radius: 4px;
  
  &:last-child {
    border-bottom: none;
  }
`

interface GameHistoryProps {
  playerHistories: HistoryStep[][]
}

export function GameHistory({ playerHistories }: GameHistoryProps) {
  return (
    <ChatPanel>
      <h2>Game History</h2>
      {playerHistories.map((playerHistory, playerIndex) => (
        playerHistory.map((step, stepIndex) => (
          <ChatMessage key={`${playerIndex}-${stepIndex}`}>
            <strong>Player {playerIndex}:</strong>{' '}
            <ReactMarkdown>{step.action}</ReactMarkdown>
          </ChatMessage>
        ))
      ))}
    </ChatPanel>
  )
}