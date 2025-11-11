# ClassMateAI - Styling Guide

## Overview
All styling for ClassMateAI has been separated into an external CSS file for easy customization and maintenance.

**Location:** `.streamlit/style.css`

## Table of Contents
- [Fonts](#fonts)
- [Colors](#colors)
- [Animations](#animations)
- [Responsive Design](#responsive-design)
- [Customization](#customization)

---

## Fonts

### Current Fonts
The application uses three Google Fonts:

1. **Inter** - Primary font for body text
   - Weights: 300, 400, 500, 600, 700, 800
   - Usage: General text, paragraphs, UI elements

2. **Poppins** - Headings font
   - Weights: 300, 400, 500, 600, 700, 800
   - Usage: All headings (h1, h2, h3, etc.)

3. **Roboto** - Monospace font
   - Weights: 300, 400, 500, 700
   - Usage: Code blocks, technical text

### Adding Custom Fonts

To add or change fonts:

1. Find your font on [Google Fonts](https://fonts.google.com/)
2. Add the import to the top of `.streamlit/style.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=YourFont:wght@400;700&display=swap');
```

3. Update the CSS variable:

```css
:root {
    --font-primary: 'YourFont', sans-serif;
}
```

### Font Variables

```css
--font-primary: 'Inter'     /* Body text */
--font-headings: 'Poppins'  /* Headings */
--font-mono: 'Roboto Mono'  /* Code/monospace */
```

---

## Colors

### Color Variables

All colors are defined as CSS variables in `:root`:

```css
/* Primary Colors */
--primary-color: #667eea
--secondary-color: #764ba2
--primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%)

/* Background Colors */
--dark-bg: #1e1e2e
--dark-border: #4a5568
--white: #ffffff
--light-gray: #f1f5f9

/* Text Colors */
--text-primary: #2d3748
--text-secondary: #94a3b8

/* Status Colors */
--success: #10b981
--warning: #f59e0b
--error: #ef4444
```

### Changing Colors

To change the color scheme:

1. Open `.streamlit/style.css`
2. Find the `:root` section
3. Update the hex values:

```css
:root {
    --primary-color: #your-color;  /* Change this */
}
```

4. All UI elements will automatically update!

---

## Animations

### Available Animations

#### 1. **fadeIn**
Fades elements in smoothly
```css
animation: fadeIn 0.5s ease-out;
```

#### 2. **slideInFromLeft**
Slides content from the left
```css
animation: slideInFromLeft 0.3s ease;
```

#### 3. **slideInFromRight**
Slides content from the right
```css
animation: slideInFromRight 0.3s ease;
```

#### 4. **scaleIn**
Scales elements in from 95% to 100%
```css
animation: scaleIn 0.3s ease;
```

#### 5. **pulse**
Pulsing opacity effect
```css
animation: pulse 2s infinite;
```

#### 6. **shimmer**
Shimmer/loading effect
```css
animation: shimmer 2s infinite;
```

### Adding Custom Animations

To add a new animation:

```css
@keyframes yourAnimation {
    from {
        /* Start state */
        opacity: 0;
        transform: scale(0.8);
    }
    to {
        /* End state */
        opacity: 1;
        transform: scale(1);
    }
}
```

Then apply it:

```css
.your-element {
    animation: yourAnimation 0.5s ease-out;
}
```

### Disabling Animations

Users who prefer reduced motion will automatically see minimal animations. To disable animations entirely, add:

```css
* {
    animation: none !important;
    transition: none !important;
}
```

---

## Responsive Design

### Breakpoints

The application uses three main breakpoints:

| Device | Max Width | Adjustments |
|--------|-----------|-------------|
| Desktop | 1024px+ | Full layout |
| Tablet | 768-1024px | Reduced padding, smaller sidebar |
| Mobile | < 768px | Stacked layout, full-width elements |
| Small Mobile | < 480px | Minimal padding, smaller fonts |

### Mobile-First Features

✅ Responsive sidebar that collapses on mobile
✅ Touch-friendly button sizes (min 44px)
✅ Readable font sizes on all screens
✅ Optimized spacing and padding
✅ Horizontal scrolling prevented

### Testing Responsiveness

Test your changes at different screen sizes:
- Desktop: 1920px, 1440px, 1280px
- Tablet: 1024px, 768px
- Mobile: 375px, 390px, 414px

Chrome DevTools: F12 → Toggle Device Toolbar (Ctrl+Shift+M)

---

## Customization

### Common Customizations

#### 1. Change Button Rounded Corners

```css
:root {
    --radius-md: 12px;  /* Increase for more rounded */
}
```

#### 2. Adjust Animation Speed

```css
:root {
    --transition-fast: 0.15s ease;
    --transition-base: 0.5s ease;  /* Make slower */
}
```

#### 3. Change Shadow Intensity

```css
:root {
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.2);  /* Darker shadow */
}
```

#### 4. Adjust Sidebar Width

```css
[data-testid="stSidebar"] {
    min-width: 300px;  /* Make wider */
    max-width: 400px;
}
```

#### 5. Change Background Gradient

```css
.stApp {
    background: linear-gradient(135deg, #yourcolor1 0%, #yourcolor2 100%);
}
```

---

## File Structure

```
ClassMait/
├── .streamlit/
│   ├── style.css          ← Main CSS file
│   └── secrets.toml       ← API keys
├── app.py                 ← Loads CSS
└── STYLING.md            ← This file
```

---

## Best Practices

### 1. Use CSS Variables
Always use variables instead of hardcoded values:

✅ Good:
```css
color: var(--primary-color);
```

❌ Bad:
```css
color: #667eea;
```

### 2. Maintain Consistency
Keep spacing multiples of your base unit:
- Use: 0.25rem, 0.5rem, 1rem, 1.5rem, 2rem
- Avoid: 0.7rem, 1.3rem

### 3. Test on Real Devices
- Use Chrome DevTools
- Test on actual mobile devices
- Check touch targets are > 44px

### 4. Consider Accessibility
- Maintain color contrast ratios (WCAG AA: 4.5:1)
- Support keyboard navigation
- Test with screen readers
- Respect prefers-reduced-motion

---

## Troubleshooting

### CSS Not Loading?

1. Check file exists:
```bash
ls -la .streamlit/style.css
```

2. Restart Streamlit:
```bash
streamlit run app.py
```

3. Clear browser cache: Ctrl+Shift+R

### Animations Not Working?

- Check syntax in `@keyframes`
- Verify animation name spelling
- Check browser DevTools console for errors

### Mobile Issues?

- Test in Chrome DevTools device mode
- Check viewport meta tag
- Verify media queries are correct

---

## Resources

- [Google Fonts](https://fonts.google.com/)
- [CSS Animations Guide](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations)
- [Responsive Design](https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design)
- [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## Support

For issues or questions:
1. Check the console for CSS errors
2. Validate CSS syntax
3. Review browser compatibility
4. Open an issue on GitHub

---

**Happy Styling! 🎨**
