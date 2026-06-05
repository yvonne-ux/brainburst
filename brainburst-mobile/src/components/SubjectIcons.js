import React from 'react';
import Svg, { Text, Rect, Circle, Path, Line, Ellipse } from 'react-native-svg';

export function MathIcon({ size = 36, color = '#FF7043' }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 36 36">
      <Text y="26" fontSize="28" fill={color} fontWeight="bold">+</Text>
    </Svg>
  );
}

export function ScienceIcon({ size = 36, color = '#26A69A' }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <Rect x="14" y="3" width="8" height="12" rx="2" stroke={color} strokeWidth="2.2" />
      <Path d="M9 32 L12 16 H24 L27 32 Q18 38 9 32Z" fill={color + '33'} stroke={color} strokeWidth="2" />
      <Circle cx="18" cy="25" r="3" fill={color} />
    </Svg>
  );
}

export function EnglishIcon({ size = 36, color = '#7C5CBF' }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 36 36">
      <Text y="26" fontSize="20" fill={color} fontWeight="bold">Aa</Text>
    </Svg>
  );
}

export function ChineseIcon({ size = 36, color = '#EC407A' }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 36 36">
      <Text y="28" fontSize="24" fill={color} fontWeight="bold">文</Text>
    </Svg>
  );
}

export function ArtIcon({ size = 36, color = '#FF8F00' }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <Circle cx="18" cy="18" r="11" stroke={color} strokeWidth="2.2" />
      <Circle cx="13" cy="14" r="2.5" fill="#E53935" />
      <Circle cx="23" cy="14" r="2.5" fill="#1E88E5" />
      <Circle cx="18" cy="23" r="2.5" fill="#43A047" />
      <Circle cx="18" cy="18" r="2.5" fill={color} />
    </Svg>
  );
}
