import sys

content = open('templates/profile/dashboard.html', encoding='utf-8').read()

start_style = '      <!-- Custom Card CSS defined early -->'
end_style = '      </style>'

css_to_inject = '''      <!-- Custom Card CSS defined early -->
      <style>
        .morph-wrapper {
          display: flex;
          justify-content: center;
        }
        .morph-card {
          position: relative;
          width: 180px;
          height: 220px;
          display: flex;
          align-items: center;
          justify-content: center;
          filter: url(#morphGoo);
          cursor: pointer;
        }

        /* Основные блобы формируют карточку */
        .morph-blob {
          position: absolute;
          background: #0a0a0a;
          border-radius: 50%;
          transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .morph-blob-1 {
          width: 180px;
          height: 180px;
          top: 20px;
          left: 0;
        }

        .morph-blob-2 {
          width: 100px;
          height: 100px;
          top: -10px;
          left: 40px;
        }

        .morph-blob-3 {
          width: 80px;
          height: 80px;
          bottom: -5px;
          left: 50px;
        }

        /* При hover — блобы перестраиваются */
        .morph-card:hover .morph-blob-1 {
          border-radius: 30%;
          width: 170px;
          height: 160px;
          top: 30px;
          left: 5px;
          transform: rotate(-3deg);
        }

        .morph-card:hover .morph-blob-2 {
          width: 70px;
          height: 70px;
          top: -20px;
          left: -15px;
          transform: rotate(10deg);
        }

        .morph-card:hover .morph-blob-3 {
          width: 60px;
          height: 60px;
          bottom: -20px;
          left: 130px;
          transform: rotate(-8deg);
        }

        /* Контент */
        .morph-content {
          position: relative;
          z-index: 2;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          color: #fff;
          transition: all 0.5s ease;
        }

        .morph-icon {
          font-size: 2.2rem;
          color: rgba(255, 255, 255, 0.7);
          transition: all 0.5s ease;
        }

        .morph-card:hover .morph-icon {
          color: #fff;
          transform: translateY(-5px);
          filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.3));
        }

        .morph-label {
          font-family: "Segoe UI", system-ui, sans-serif;
          font-size: 11px;
          font-weight: 500;
          color: rgba(255, 255, 255, 0.6);
          letter-spacing: 2px;
          text-transform: uppercase;
          transition: all 0.5s ease;
        }

        .morph-card:hover .morph-label {
          color: rgba(255, 255, 255, 0.8);
          letter-spacing: 4px;
        }

        .morph-count {
          font-family: "Segoe UI", system-ui, sans-serif;
          font-size: 32px;
          font-weight: 300;
          color: #fff;
          transition: all 0.5s ease;
        }

        .morph-card:hover .morph-count {
          transform: scale(1.1);
          text-shadow: 0 0 20px rgba(255, 255, 255, 0.2);
        }

        /* Active — сжатие */
        .morph-card:active .morph-blob {
          transform: scale(0.92) !important;
          transition-duration: 0.15s;
        }
      </style>'''

old_part = content[content.find(start_style):content.find(end_style)+len(end_style)]
content = content.replace(old_part, css_to_inject)

with open('templates/profile/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
