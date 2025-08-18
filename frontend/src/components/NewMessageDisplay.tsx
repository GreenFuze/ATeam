import React from 'react';
import { MessageDisplayFactory, BaseMessageDisplayProps } from './messages';

const NewMessageDisplay: React.FC<BaseMessageDisplayProps> = (props) => {
  const ComponentClass = MessageDisplayFactory.createComponent(props);
  return React.createElement(ComponentClass, props);
};

export default NewMessageDisplay;
