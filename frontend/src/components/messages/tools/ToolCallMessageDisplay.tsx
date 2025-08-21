
import React from 'react';
import { Badge, Loader, Alert } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { ToolBaseMessageDisplay } from './ToolBaseMessageDisplay';

class ToolCallMessageDisplayClass extends ToolBaseMessageDisplay {

  componentDidMount() {
    super.componentDidMount();
  }

  componentWillUnmount() {
    super.componentWillUnmount();
  }

  getBadges(): JSX.Element[] {
    const badges = [
      <Badge key="tool-call" size="xs" variant="light" color="yellow">
        TOOL CALL
      </Badge>
    ];

    // Add streaming badges from base class
    badges.push(...this.getStreamingBadges());

    return badges;
  }

  renderToolContent(): JSX.Element {
    const { message } = this.props;

    return (
      <div>
        <div>Calling tool {message.tool_name}</div>
        {this.renderToolMetadata()}
        
        {/* Streaming content area */}
        {message.is_streaming && (
          <div style={{ marginTop: '12px' }}>
            {this.state.isStreaming && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                padding: '8px',
                backgroundColor: 'rgba(0,255,0,0.1)',
                borderRadius: '4px',
                border: '1px solid rgba(0,255,0,0.3)'
              }}>
                <Loader size="xs" color="green" />
                <span style={{ color: 'green', fontSize: '12px' }}>
                  Executing tool... {this.state.streamContent && `(${this.state.streamContent.length} chars received)`}
                </span>
              </div>
            )}
            
            {this.state.streamError && (
              <Alert 
                icon={<IconAlertCircle size={16} />} 
                title="Stream Error" 
                color="red"
                style={{ marginTop: '8px' }}
              >
                {this.state.streamError}
              </Alert>
            )}
            
            {this.state.streamComplete && this.state.streamContent && (
              <div style={{ 
                marginTop: '8px',
                padding: '8px',
                backgroundColor: 'rgba(255,255,255,0.05)',
                borderRadius: '4px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <strong>Result:</strong>
                <div style={{ 
                  marginTop: '4px',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'Consolas, "Courier New", monospace',
                  fontSize: '12px'
                }}>
                  {this.state.streamContent}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  renderToolMetadata(): JSX.Element | null {
    const { message } = this.props;
    const metadataItems = [];

    if (message.tool_parameters) {
      metadataItems.push(
        <div key="params" style={{ marginTop: '4px', padding: '8px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '4px' }}>
          <strong>Parameters:</strong> <span style={{ fontFamily: 'Consolas, "Courier New", monospace' }}>{JSON.stringify(message.tool_parameters)}</span>
        </div>
      );
    }

    return metadataItems.length > 0 ? (
      <div style={{ marginTop: '8px' }}>
        {metadataItems}
      </div>
    ) : null;
  }
}

// Memoized export for performance optimization
export const ToolCallMessageDisplay = React.memo(ToolCallMessageDisplayClass);
