import './style.css';
import 'flowbite/dist/flowbite.js';
import './sidebar';
import './dark-mode';

import {select, selectAll, arc, pie, interpolate, scaleLinear, scaleThreshold} from 'd3';

import '@xterm/xterm/css/xterm.css';
import { Terminal } from '@xterm/xterm';
import { ClipboardAddon } from '@xterm/addon-clipboard';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { WebglAddon } from '@xterm/addon-webgl';

const d3 = {select, selectAll, arc, pie, interpolate, scaleLinear, scaleThreshold};
window.d3 = d3;

window.Terminal = Terminal;
window.ClipboardAddon = ClipboardAddon;
window.FitAddon = FitAddon;
window.WebglAddon = WebglAddon;
window.WebLinksAddon = WebLinksAddon;
