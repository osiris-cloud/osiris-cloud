import '@xterm/xterm/css/xterm.css';
import { Terminal } from '@xterm/xterm';
import { ClipboardAddon } from '@xterm/addon-clipboard';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { WebglAddon } from '@xterm/addon-webgl';

window.Terminal = Terminal;
window.ClipboardAddon = ClipboardAddon;
window.FitAddon = FitAddon;
window.WebglAddon = WebglAddon;
window.WebLinksAddon = WebLinksAddon;
