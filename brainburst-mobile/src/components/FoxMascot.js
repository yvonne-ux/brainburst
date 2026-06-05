import React from 'react';
import { Image } from 'react-native';

export default function FoxMascot({ size = 140, style }) {
  return (
    <Image
      source={require('../../assets/dog.png')}
      style={[{ width: size, height: size, resizeMode: 'contain' }, style]}
    />
  );
}
