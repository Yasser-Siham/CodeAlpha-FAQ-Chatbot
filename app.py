"""Offline FAQ assistant with a responsive, canvas-drawn desktop interface."""
import math
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

from chatbot import FAQChatbot

BG = '#151719'
SIDE = '#101214'
SURFACE = '#222629'
TEXT = '#f1f4f3'
MUTED = '#929d9c'
MINT = '#84eed2'


def blend(a, b, t):
    values = [round(int(a[i:i+2], 16)*(1-t) + int(b[i:i+2], 16)*t) for i in (1, 3, 5)]
    return '#' + ''.join(f'{v:02x}' for v in values)


def rounded(c, x, y, w, h, r=18, fill=SURFACE, outline='', tags=()):
    r = min(r, w/2, h/2)
    return c.create_polygon(x+r, y, x+w-r, y, x+w, y, x+w, y+r,
                            x+w, y+h-r, x+w, y+h, x+w-r, y+h,
                            x+r, y+h, x, y+h, x, y+h-r, x, y+r, x, y,
                            smooth=True, splinesteps=32, fill=fill,
                            outline=outline, width=1, tags=tags)


def elevated(c, x, y, w, h, r=18, fill=SURFACE, tags=(), lift=0):
    for offset, color in [(7, '#111314'), (4, '#121516'), (2, '#171b1c')]:
        rounded(c, x, y+offset, w, h, r, color, tags=tags)
    rounded(c, x, y-lift, w, h, r, fill, '#37403f', tags)
    c.create_line(x+r, y+1-lift, x+w-r, y+1-lift, fill='#424c4a', tags=tags)


class FAQChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CodeAlpha | Assistant')
        self.geometry('1180x820')
        self.minsize(760, 600)
        self.configure(bg=BG)
        self.bot = FAQChatbot(Path(__file__).parent / 'data/faqs.json')
        self.history = []
        self.busy = False
        self.phase = 0
        self.hovered = None
        self.message_bounds = []
        self.follow_bottom = True
        self.body_font = tkfont.Font(family='Segoe UI', size=12)
        self._build_ui()
        self._tick_id = self.after(50, self._tick)

    def destroy(self):
        if hasattr(self, '_tick_id'):
            self.after_cancel(self._tick_id)
        super().destroy()

    def _canvas(self, parent, **kw):
        return tk.Canvas(parent, bg=BG, highlightthickness=0, bd=0, **kw)

    def _text(self, c, x, y, text, size=11, color=TEXT, bold=False, **kw):
        return c.create_text(x, y, text=text, fill=color, anchor='nw',
                             font=('Segoe UI', size, 'bold' if bold else 'normal'), **kw)

    def _build_ui(self):
        self.sidebar = tk.Canvas(self, width=202, bg=SIDE, highlightthickness=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.bind('<Configure>', lambda e: self._draw_sidebar())
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side='left', fill='both', expand=True)
        self.header = self._canvas(self.main, height=74)
        self.header.pack(fill='x')
        self.header.bind('<Configure>', lambda e: self._draw_header())
        self.footer = self._canvas(self.main, height=134)
        self.footer.pack(side='bottom', fill='x')
        self.input_value = tk.StringVar()
        self.entry = tk.Entry(self.footer, textvariable=self.input_value, font=('Segoe UI', 12),
                              bg=SURFACE, fg=TEXT, insertbackground=MINT, relief='flat', bd=0,
                              selectbackground='#3d675d')
        self.entry.bind('<Return>', lambda e: self.send_message())
        self.entry.bind('<FocusIn>', lambda e: self._draw_composer())
        self.entry.bind('<FocusOut>', lambda e: self._draw_composer())
        self.input_value.trace_add('write', lambda *args: self._draw_composer())
        self.entry_window = self.footer.create_window(0, 0, window=self.entry, anchor='nw')
        self.footer.bind('<Configure>', lambda e: self._draw_composer())
        self.stage = tk.Frame(self.main, bg=BG)
        self.stage.pack(fill='both', expand=True)
        self.canvas = self._canvas(self.stage, yscrollincrement=28)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar = tk.Scrollbar(self.stage, orient='vertical', command=self._scrollbar,
                                      bg='#303638', troughcolor=BG, activebackground='#4c5c58',
                                      relief='flat', bd=0, width=10, highlightthickness=0)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self._render())
        self.canvas.bind('<MouseWheel>', self._wheel)
        self.canvas.bind('<Button-4>', lambda e: self._wheel_units(-3))
        self.canvas.bind('<Button-5>', lambda e: self._wheel_units(3))
        self.canvas.bind('<Motion>', self._hover)
        self.canvas.bind('<Leave>', lambda e: self._set_hover(None))
        self.bind('<Control-n>', lambda e: self._reset())
        self.entry.focus_set()

    def _draw_sidebar(self):
        c = self.sidebar
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        c.create_oval(22, 24, 56, 58, fill=MINT, outline='')
        self._text(c, 29, 30, 'ca', 12, '#13352c', True)
        self._text(c, 67, 29, 'CodeAlpha', 13, bold=True)
        elevated(c, 15, 90, w-30, 44, 14, '#262d2d', tags=('new',))
        self._text(c, 29, 101, '+   New chat', 11, tags=('new',))
        c.tag_bind('new', '<Button-1>', lambda e: self._reset())
        c.tag_bind('new', '<Enter>', lambda e: c.configure(cursor='hand2'))
        c.tag_bind('new', '<Leave>', lambda e: c.configure(cursor=''))
        self._text(c, 25, 171, 'YOUR SPACE', 8, MUTED, True)
        rounded(c, 15, 198, w-30, 42, 12, '#1b2925')
        self._text(c, 29, 209, '◈   FAQ assistant', 10, MINT)
        self._text(c, 25, 280, 'Made for your next step.', 9, '#626f6c', width=w-45)
        c.create_line(22, h-85, w-22, h-85, fill='#282e2d')
        c.create_oval(24, h-56, 32, h-48, fill=MINT, outline='')
        self._text(c, 42, h-61, 'Local & private', 9, MUTED)

    def _draw_header(self):
        c = self.header
        c.delete('all')
        self._text(c, 30, 24, 'Assistant', 14, bold=True)
        self._text(c, 132, 29, '/  CodeAlpha', 10, MUTED)
        w = c.winfo_width()
        rounded(c, w-146, 23, 116, 28, 14, '#202c27')
        self._text(c, w-131, 29, '●  Offline ready', 9, MINT)

    def _draw_composer(self):
        c = self.footer
        c.delete('chrome')
        w = min(800, c.winfo_width()-64)
        x = (c.winfo_width()-w)/2
        elevated(c, x, 14, w, 74, 25, SURFACE, ('chrome',))
        self._text(c, x+20, 37, '✦', 19, MINT, tags=('chrome',))
        c.coords(self.entry_window, x+58, 36)
        c.itemconfigure(self.entry_window, width=max(100, w-132), height=30)
        if not self.input_value.get() and self.focus_get() != self.entry:
            self._text(c, x+60, 40, 'Ask anything about CodeAlpha…', 11, MUTED, tags=('chrome', 'placeholder'))
            c.tag_bind('placeholder', '<Button-1>', lambda e: self.entry.focus_set())
        elevated(c, x+w-59, 29, 43, 43, 15, '#487a6c' if self.busy else MINT, ('chrome', 'send'))
        self._text(c, x+w-45, 34, '↑', 21, '#15392e', True, tags=('chrome', 'send'))
        c.tag_bind('send', '<Button-1>', lambda e: self.send_message())
        c.tag_bind('send', '<Enter>', lambda e: c.configure(cursor='hand2'))
        c.tag_bind('send', '<Leave>', lambda e: c.configure(cursor=''))
        c.create_text(c.winfo_width()/2, 111, text='Answers from your FAQ library  ·  Enter to send',
                      font=('Segoe UI', 9), fill='#727e7b', tags='chrome')
        c.tag_raise(self.entry_window)

    def _orb(self, c, x, y):
        c.delete('orb')
        dy = math.sin(self.phase/16)*5
        for i in range(8):
            c.create_oval(x-40+i*3, y+53-i/2, x+40-i*3, y+66+i/2,
                          fill=blend(BG, '#050908', .3+i*.06), outline='', tags='orb')
        for r, color in [(64, '#182320'), (56, '#1b2d27')]:
            c.create_oval(x-r, y-r+dy, x+r, y+r+dy, fill=color, outline='', tags='orb')
        for i in range(46):
            r = 46-i*.87
            cx, cy = x-i*.32, y-i*.42+dy
            color = blend('#154b44', '#c5ffdf', i/45)
            c.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline='', tags='orb')
        c.create_arc(x-66, y-25+dy, x+66, y+27+dy, start=185, extent=165,
                     style='arc', outline='#70ceb4', width=2, tags='orb')
        c.create_text(x, y+dy, text='✦', font=('Segoe UI', 28), fill='#f0fff7', tags='orb')

    def _render_hero(self):
        c = self.canvas
        w, h = c.winfo_width(), c.winfo_height()
        cx, top = w/2, max(70, (h-375)/2)
        self.orb_position = (cx, top)
        self._orb(c, cx, top)
        c.create_text(cx, top+106, text='What’s your next move?', font=('Segoe UI', 27, 'bold'), fill=TEXT)
        c.create_text(cx, top+148, text='Less searching. More creating.', font=('Segoe UI', 12), fill=MUTED)
        total = min(710, w-54)
        gap = 14
        cw = (total-gap*2)/3
        self.card_regions = []
        topics = [('↗', 'Ship your project', 'Submission & GitHub', 'How do I submit my completed task?'),
                  ('◇', 'Make it official', 'Certificates & progress', 'Will I receive a certificate?'),
                  ('✦', 'Behind the scenes', 'Meet your assistant', 'How does this chatbot understand my question?')]
        for i, (icon, title, sub, question) in enumerate(topics):
            x, y = cx-total/2+i*(cw+gap), top+198
            lift = 5 if self.hovered == i else 0
            tag = f'topic{i}'
            elevated(c, x, y, cw, 116, 20, '#293b34' if self.hovered == i else '#232a28', (tag,), lift)
            rounded(c, x+17, y+16-lift, 30, 30, 10, '#344c41', tags=(tag,))
            self._text(c, x+25, y+19-lift, icon, 15, MINT, tags=(tag,))
            self._text(c, x+17, y+59-lift, title, 10, bold=True, tags=(tag,))
            self._text(c, x+17, y+83-lift, sub, 8, MUTED, tags=(tag,))
            c.tag_bind(tag, '<Button-1>', lambda e, q=question: self._ask(q))
            self.card_regions.append((x, y-6, x+cw, y+116, i))
        c.configure(scrollregion=(0, 0, w, h))

    def _render(self):
        c = self.canvas
        c.delete('all')
        self.message_bounds = []
        if not self.history:
            self.scrollbar.pack_forget()
            self._render_hero()
            return
        if not self.scrollbar.winfo_ismapped():
            self.scrollbar.pack(side='right', fill='y')
        w = c.winfo_width()
        width = min(760, w-56)
        left = (w-width)/2
        y = 22
        for sender, message in self.history:
            if sender == 'user':
                wrap = max(150, width*.78-40)
                # Measure on the same canvas that displays the text; height remains correct after resizing.
                item = c.create_text(0, 0, text=message, width=wrap, font=self.body_font, anchor='nw')
                box = c.bbox(item)
                tw, th = box[2]-box[0], box[3]-box[1]
                c.delete(item)
                bw, bh = tw+36, th+28
                x = left+width-bw
                elevated(c, x, y, bw, bh, 20, '#2a3e37')
                item = c.create_text(x+18, y+14, text=message, width=wrap, font=self.body_font, fill='#e1f8ef', anchor='nw')
                self.message_bounds.append(c.bbox(item))
                y += bh+30
            else:
                rounded(c, left, y, 29, 29, 10, '#29483c')
                self._text(c, left+7, y+2, '✦', 14, MINT)
                self._text(c, left+42, y+3, 'CodeAlpha', 10, bold=True)
                item = c.create_text(left+42, y+33, text=message, width=max(150, width-50),
                                      font=self.body_font, fill='#d8dfdc', anchor='nw')
                box = c.bbox(item)
                self.message_bounds.append(box)
                y = box[3]+32
        if self.busy:
            self._text(c, left+42, y, '✦  Thinking' + '.'*(self.phase//3 % 4), 10, MINT, tags='thinking')
            y += 38
        self.content_height = y+28
        c.configure(scrollregion=(0, 0, w, max(c.winfo_height(), self.content_height)))
        if self.follow_bottom:
            c.yview_moveto(1)

    def _hover(self, event):
        if self.history:
            return
        found = None
        for x, y, xx, yy, index in getattr(self, 'card_regions', []):
            if x <= event.x <= xx and y <= event.y <= yy:
                found = index
        self._set_hover(found)

    def _set_hover(self, index):
        if self.hovered != index:
            self.hovered = index
            self.canvas.configure(cursor='hand2' if index is not None else '')
            if not self.history:
                self._render()

    def _tick(self):
        self.phase += 1
        if not self.history and hasattr(self, 'orb_position'):
            self._orb(self.canvas, *self.orb_position)
        elif self.busy:
            self.canvas.itemconfigure('thinking', text='✦  Thinking' + '.'*(self.phase//3 % 4))
        self._tick_id = self.after(50, self._tick)

    def _wheel_units(self, units):
        if self.history:
            self.canvas.yview_scroll(units, 'units')
            self.follow_bottom = self.canvas.yview()[1] >= .995

    def _wheel(self, event):
        self._wheel_units(-int(event.delta/120)*2)
        return 'break'

    def _scrollbar(self, *args):
        self.canvas.yview(*args)
        self.follow_bottom = self.canvas.yview()[1] >= .995

    def _reset(self):
        if self.busy:
            return
        self.history.clear()
        self.hovered = None
        self.follow_bottom = True
        self.input_value.set('')
        self._render()
        self.entry.focus_set()

    def _ask(self, question):
        if not self.busy:
            self.input_value.set(question)
            self.send_message()

    def send_message(self):
        message = self.input_value.get().strip()
        if not message or self.busy:
            return
        self.history.append(('user', message))
        self.input_value.set('')
        self.busy = True
        self.follow_bottom = True
        self._draw_composer()
        self._render()
        self.after(90, lambda: self._respond(message))

    def _respond(self, message):
        try:
            response, _, _ = self.bot.get_response(message)
        except Exception:
            response = 'Something went wrong. Please try your question again.'
        self.history.append(('bot', response))
        self.busy = False
        self._draw_composer()
        self._render()
        self.entry.focus_set()


if __name__ == '__main__':
    FAQChatApp().mainloop()
