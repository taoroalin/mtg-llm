import styled from '@emotion/styled';

const CodePanel = styled.div`
  background: #e8e8e8;
  padding: 15px;
  border-radius: 8px;
  height: calc(100vh - 40px);
  overflow-y: auto;
`;

const CodeBlock = styled.pre`
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 10px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-width: 80ch;
  font-family: monospace;
  font-size: 14px;
  
  /* Add visual indicator for long lines */
  &::before {
    content: '';
    position: absolute;
    right: 0;
    width: 2px;
    height: 100%;
    background: #ddd;
  }
`;

interface CodeHistoryProps {
  codeHistory: string[];
  errorHistory: string[];
}
export function CodeHistory({ codeHistory, errorHistory }: CodeHistoryProps) {
  const wrapCode = (code: string): string => {
    const lines = code.split('\n');
    return lines
      .map(line => {
        const chunks = [];
        for (let i = 0; i < line.length; i += 80) {
          chunks.push(line.slice(i, i + 80));
        }
        return chunks.join('\n');
      })
      .join('\n');
  };

  return (
    <CodePanel>
      <h2>Executed Code</h2>
      {codeHistory.map((code, index) => (
        <CodeBlock key={`code-${index}`}>{wrapCode(code)}</CodeBlock>
      ))}
      
      {errorHistory.length > 0 && (
        <>
          <h2>Errors</h2>
          {errorHistory.map((error, index) => (
            <CodeBlock key={`error-${index}`} style={{color: 'red'}}>{error}</CodeBlock>
          ))}
        </>
      )}
    </CodePanel>
  );
}