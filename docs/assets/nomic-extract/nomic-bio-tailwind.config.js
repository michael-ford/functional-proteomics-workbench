/** @type {import('tailwindcss').Config} */
export default {
  theme: {
    extend: {
    colors: {
        primary: {
            '50': 'hsl(240, 65%, 97%)',
            '100': 'hsl(240, 65%, 94%)',
            '200': 'hsl(240, 65%, 86%)',
            '300': 'hsl(240, 65%, 76%)',
            '400': 'hsl(240, 65%, 64%)',
            '500': 'hsl(240, 65%, 50%)',
            '600': 'hsl(240, 65%, 40%)',
            '700': 'hsl(240, 65%, 32%)',
            '800': 'hsl(240, 65%, 24%)',
            '900': 'hsl(240, 65%, 16%)',
            '950': 'hsl(240, 65%, 10%)',
            DEFAULT: '#4a4ad8'
        },
        secondary: {
            '50': 'hsl(147, 65%, 97%)',
            '100': 'hsl(147, 65%, 94%)',
            '200': 'hsl(147, 65%, 86%)',
            '300': 'hsl(147, 65%, 76%)',
            '400': 'hsl(147, 65%, 64%)',
            '500': 'hsl(147, 65%, 50%)',
            '600': 'hsl(147, 65%, 40%)',
            '700': 'hsl(147, 65%, 32%)',
            '800': 'hsl(147, 65%, 24%)',
            '900': 'hsl(147, 65%, 16%)',
            '950': 'hsl(147, 65%, 10%)',
            DEFAULT: '#4ad889'
        },
        accent: {
            '50': 'hsl(231, 64%, 97%)',
            '100': 'hsl(231, 64%, 94%)',
            '200': 'hsl(231, 64%, 86%)',
            '300': 'hsl(231, 64%, 76%)',
            '400': 'hsl(231, 64%, 64%)',
            '500': 'hsl(231, 64%, 50%)',
            '600': 'hsl(231, 64%, 40%)',
            '700': 'hsl(231, 64%, 32%)',
            '800': 'hsl(231, 64%, 24%)',
            '900': 'hsl(231, 64%, 16%)',
            '950': 'hsl(231, 64%, 10%)',
            DEFAULT: '#a0abea'
        },
        'neutral-50': '#ffffff',
        'neutral-100': '#e4e5ee',
        'neutral-200': '#000000',
        'neutral-300': '#ece4ff',
        'neutral-400': '#dddddd',
        background: '#090426',
        foreground: '#000000'
    },
    fontFamily: {
        sans: [
            'Outfit Variablefont Wght',
            'sans-serif'
        ],
        heading: [
            'Arial',
            'sans-serif'
        ],
        body: [
            'WistiaPlayerInter',
            'sans-serif'
        ]
    },
    fontSize: {
        '12': [
            '12px',
            {
                lineHeight: '18px'
            }
        ],
        '13': [
            '13px',
            {
                lineHeight: '19.5px'
            }
        ],
        '14': [
            '14px',
            {
                lineHeight: '24.5px'
            }
        ],
        '16': [
            '16px',
            {
                lineHeight: 'normal'
            }
        ],
        '18': [
            '18px',
            {
                lineHeight: '25.2px'
            }
        ],
        '20': [
            '20px',
            {
                lineHeight: '28px'
            }
        ],
        '24': [
            '24px',
            {
                lineHeight: '36px'
            }
        ],
        '32': [
            '32px',
            {
                lineHeight: '41.6px'
            }
        ],
        '42': [
            '42px',
            {
                lineHeight: '50.4px'
            }
        ],
        '64': [
            '64px',
            {
                lineHeight: '70.4px'
            }
        ]
    },
    spacing: {
        '12': '24px',
        '24': '48px',
        '27': '54px',
        '32': '64px',
        '40': '80px',
        '48': '96px',
        '56': '112px',
        '80': '160px',
        '3px': '3px',
        '31px': '31px',
        '171px': '171px',
        '181px': '181px',
        '441px': '441px'
    },
    borderRadius: {
        sm: '5px',
        md: '9px',
        lg: '15px',
        xl: '24px',
        full: '160px'
    },
    boxShadow: {
        sm: 'rgb(255, 255, 255) 0px 0px 0px 2px inset',
        lg: 'rgba(249, 107, 107, 0.35) 0px 10px 20px -2px',
        xl: 'rgba(0, 0, 0, 0.28) 0px 8px 28px 0px'
    },
    screens: {
        md: '768px'
    },
    transitionDuration: {
        '100': '0.1s',
        '150': '0.15s',
        '200': '0.2s',
        '300': '0.3s',
        '400': '0.4s',
        '500': '0.5s',
        '600': '0.6s',
        '1000': '1s',
        '2000': '2s',
        '44000': '44s'
    },
    transitionTimingFunction: {
        default: 'ease',
        linear: 'linear'
    },
    container: {
        center: true,
        padding: '0px'
    },
    maxWidth: {
        container: 'calc(100% - 64px)'
    }
},
  },
};
