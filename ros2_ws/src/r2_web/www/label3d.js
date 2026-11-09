// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// A text label for the 3D views that always faces the camera (a sprite drawn on a canvas).
import * as THREE from 'three';

/** A sprite showing text, heightM tall in metres (its width follows the text). */
export function textSprite(text, color = '#56d364', heightM = 0.07) {
  const px = 64, c = document.createElement('canvas'), g = c.getContext('2d');
  g.font = `bold ${px}px system-ui, sans-serif`;
  c.width = Math.ceil(g.measureText(text).width) + px / 2; c.height = px * 1.4;
  g.font = `bold ${px}px system-ui, sans-serif`;
  g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineWidth = px / 6; g.strokeStyle = '#0d1117'; g.strokeText(text, c.width / 2, c.height / 2);
  g.fillStyle = color; g.fillText(text, c.width / 2, c.height / 2);
  const tex = new THREE.CanvasTexture(c);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  s.scale.set(heightM * c.width / c.height, heightM, 1);
  s.renderOrder = 10;
  return s;
}
