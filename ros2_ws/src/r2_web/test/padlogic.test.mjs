// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { BUTTONS, createPad, maskOf } from '../www/padlogic.js';

test('button bits as the Mega reads them (DroidButton)', () => {
  assert.deepEqual(BUTTONS, ['UP', 'DOWN', 'LEFT', 'RIGHT', 'CROSS', 'CIRCLE', 'L1', 'L2', 'L3', 'PS']);
  assert.equal(maskOf(['PS', 'L2']), 0x0280);
  assert.equal(maskOf([]), 0);
});

test('a short click presses and releases', () => {
  const p = createPad();
  p.down('CROSS', 0);
  assert.equal(p.up('CROSS', 100).action, 'tap');
  assert.equal(p.state(150).buttons, maskOf(['CROSS']));
  assert.equal(p.state(399).buttons, maskOf(['CROSS']));
  assert.equal(p.state(400).buttons, 0);           // comboMs after the release
  assert.equal(p.active(400), false);
});

test('a long press holds; the next button sends the combination and clears the hold', () => {
  const p = createPad();
  p.down('PS', 0);
  assert.deepEqual(p.tick(599), []);
  assert.deepEqual(p.tick(600), ['PS']);            // HOLD while still pressed
  assert.equal(p.up('PS', 700).action, 'hold');
  assert.ok(p.held().has('PS'));
  assert.equal(p.state(800).buttons, maskOf(['PS']));
  assert.equal(p.active(800), true);
  p.down('L2', 1000);
  assert.equal(p.up('L2', 1050).action, 'combo');
  assert.equal(p.state(1100).buttons, 0x0280);
  assert.equal(p.held().size, 0);
  assert.equal(p.state(1350).buttons, 0);
});

test('a long press without tick still holds on release', () => {
  const p = createPad();
  p.down('L1', 0);
  assert.equal(p.up('L1', 700).action, 'hold');
  assert.ok(p.held().has('L1'));
});

test('long press, then a click on the same button lets it go (the mock bug)', () => {
  const p = createPad();
  p.down('L1', 0);
  p.tick(650);
  p.up('L1', 700);
  p.down('L1', 900);
  assert.equal(p.up('L1', 950).action, 'let-go');
  assert.equal(p.held().size, 0);
  assert.equal(p.state(960).buttons, 0);
});

test('two held and a third click: a three-button combination', () => {
  const p = createPad();
  p.down('PS', 0); p.up('PS', 700);
  p.down('L1', 800); p.up('L1', 1500);
  p.down('CROSS', 1600);
  assert.equal(p.up('CROSS', 1650).action, 'combo');
  assert.equal(p.state(1700).buttons, 0x0250);
  assert.equal(p.state(1950).buttons, 0);
  assert.equal(p.held().size, 0);
});

test('a hold stays pressed while the stick moves and goes when the stick is let go', () => {
  const p = createPad();
  p.down('L1', 0); p.up('L1', 700);
  p.stick(200, 128);
  let s = p.state(800);
  assert.equal(s.buttons, maskOf(['L1']));
  assert.equal(s.x, 200);
  p.stickUp();
  s = p.state(900);
  assert.equal(s.x, 128);
  assert.equal(s.buttons, 0);
  assert.equal(p.held().size, 0);
});

test('Esc lets every hold go and sends nothing else', () => {
  const p = createPad();
  p.down('PS', 0); p.up('PS', 700);
  p.down('L2', 800); p.up('L2', 1500);
  p.esc();
  assert.equal(p.held().size, 0);
  assert.equal(p.state(1600).buttons, 0);
  assert.equal(p.active(1600), false);
});

test('reset lets everything go at once (window closed, tab hidden)', () => {
  const p = createPad();
  p.down('PS', 0); p.up('PS', 700);
  p.stick(10, 10);
  p.reset();
  assert.deepEqual(p.state(800), { buttons: 0, x: 128, y: 128 });
  assert.equal(p.active(800), false);
});
