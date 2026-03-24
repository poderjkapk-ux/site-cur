# tpl_client_web.py

WEB_ORDER_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{site_title}</title>
    <meta name="description" content="{seo_description}">
    <meta name="keywords" content="{seo_keywords}">
    
    <meta property="og:type" content="website">
    <meta property="og:title" content="{site_title}">
    <meta property="og:description" content="{seo_description}">
    <meta property="og:image" content="/{header_image_url}">
    <meta property="og:site_name" content="{site_title}">
    
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{site_title}">
    <meta name="twitter:description" content="{seo_description}">
    <meta name="twitter:image" content="/{header_image_url}">

    <script type="application/ld+json">
        {schema_json}
    </script>
    
    <link rel="apple-touch-icon" sizes="180x180" href="/static/favicons/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicons/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicons/favicon-16x16.png">
    <link rel="manifest" href="/static/favicons/site.webmanifest">
    <link rel="shortcut icon" href="/static/favicons/favicon.ico">
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family={font_family_serif_encoded}:wght@400;600;700&family={font_family_sans_encoded}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
      :root {{
        /* --- Dynamic Variables --- */
        --primary: {primary_color_val};
        --secondary: {secondary_color_val};
        --bg-color: {background_color_val};
        --text-main: {text_color_val};
        --footer-bg: {footer_bg_color_val};
        --footer-text: {footer_text_color_val};
        --nav-bg: {category_nav_bg_color};
        --nav-text: {category_nav_text_color};
        --header-img: url('/{header_image_url}');
        
        /* --- System Colors & Shadows --- */
        --surface: #ffffff;
        --surface-glass: rgba(255, 255, 255, 0.95);
        --border-light: rgba(0, 0, 0, 0.08);
        
        --shadow-sm: 0 4px 12px rgba(0,0,0,0.05);
        --shadow-md: 0 12px 30px rgba(0,0,0,0.08);
        --shadow-lg: 0 20px 60px rgba(0,0,0,0.15);
        --shadow-float: 0 15px 35px rgba(0,0,0,0.2);
        
        /* --- Geometry --- */
        --radius-lg: 24px;
        --radius-md: 16px;
        --radius-sm: 10px;
        
        /* --- Animation --- */
        --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
        --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
        
        /* --- Fonts --- */
        --font-sans: '{font_family_sans_val}', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        --font-serif: '{font_family_serif_val}', serif;
      }}
      
      html {{ scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }}
      * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }}
      
      body {{
        margin: 0;
        background-color: var(--bg-color);
        background-image: 
            radial-gradient(at 0% 0%, color-mix(in srgb, var(--primary), transparent 97%), transparent 60%),
            radial-gradient(at 100% 100%, color-mix(in srgb, var(--secondary), transparent 97%), transparent 60%);
        background-attachment: fixed;
        color: var(--text-main);
        font-family: var(--font-sans);
        display: flex; flex-direction: column; min-height: 100vh;
        -webkit-font-smoothing: antialiased;
        font-size: 15px;
        line-height: 1.5;
      }}

      h1, h2, h3, h4, .serif {{ font-family: var(--font-serif); margin: 0; color: var(--text-main); }}
      button, input, textarea, select {{ font-family: var(--font-sans); }}

      /* --- PREMIUM HEADER --- */
      header {{
          position: relative;
          height: 45vh; min-height: 350px; max-height: 500px;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          text-align: center; color: white;
          border-radius: 0 0 50px 50px;
          overflow: hidden;
          box-shadow: 0 10px 50px rgba(0,0,0,0.15);
          margin-bottom: 20px;
      }}
      .header-bg {{
          position: absolute; inset: 0;
          background-image: var(--header-img);
          background-size: cover; background-position: center;
          z-index: 0; transition: transform 10s ease;
      }}
      header:hover .header-bg {{ transform: scale(1.05); }}
      header::after {{
          content: ''; position: absolute; inset: 0;
          background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.7));
          z-index: 1;
          backdrop-filter: blur(1px);
      }}
      
      .header-content {{ position: relative; z-index: 2; width: 90%; max-width: 800px; animation: fadeUp 1s var(--ease-out); }}
      .header-logo {{ 
          height: 110px; width: auto; margin-bottom: 20px; 
          filter: drop-shadow(0 10px 25px rgba(0,0,0,0.3));
          transition: transform 0.3s ease;
      }}
      .header-logo:hover {{ transform: scale(1.05) rotate(-2deg); }}
      header h1 {{ 
          font-size: clamp(2.2rem, 6vw, 4rem); font-weight: 700; 
          text-shadow: 0 4px 25px rgba(0,0,0,0.4); line-height: 1.1; letter-spacing: -0.02em; color: white;
      }}

      /* --- HEADER INFO ACTIONS --- */
      .header-info-actions {{
          margin-top: 25px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 15px;
          animation: fadeUp 1.2s var(--ease-out);
      }}
      
      .header-address {{
          color: rgba(255, 255, 255, 0.95);
          text-decoration: none;
          font-size: 1rem;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 8px;
          transition: all 0.3s;
          text-shadow: 0 2px 10px rgba(0,0,0,0.5);
          background: rgba(0,0,0,0.2);
          padding: 6px 16px;
          border-radius: 50px;
          backdrop-filter: blur(4px);
      }}
      .header-address:hover {{
          color: white;
          transform: scale(1.05);
          background: rgba(0,0,0,0.4);
      }}

      .header-book-btn {{
          background: rgba(255, 255, 255, 0.2);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.4);
          padding: 12px 28px;
          border-radius: 50px;
          color: white;
          text-decoration: none;
          font-weight: 700;
          font-size: 1rem;
          transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
          display: flex;
          align-items: center;
          gap: 10px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      }}
      .header-book-btn:hover {{
          background: white;
          color: var(--primary);
          transform: translateY(-3px);
          box-shadow: 0 10px 30px rgba(0,0,0,0.25);
          border-color: white;
      }}
      .header-book-btn:active {{ transform: scale(0.96); }}

      @media (min-width: 768px) {{
          .header-info-actions {{
              flex-direction: row;
              justify-content: center;
              gap: 30px;
          }}
          .header-address {{
             font-size: 1.1rem;
             background: transparent; 
             padding: 0;
             backdrop-filter: none;
          }}
          .header-address:hover {{ background: transparent; transform: scale(1.1); }}
      }}

      /* --- HERO SLIDER (WIDE ADAPTIVE) --- */
      .hero-slider-container {{
          width: 100%; 
          max-width: 1800px; 
          margin: 0 auto 40px auto; 
          padding: 0 25px;
          position: relative; overflow: hidden;
      }}
      .hero-slider {{
          display: flex; gap: 20px; overflow-x: auto; scroll-snap-type: x mandatory;
          scrollbar-width: none; -ms-overflow-style: none; padding-bottom: 10px;
      }}
      .hero-slider::-webkit-scrollbar {{ display: none; }}
      
      .hero-slide {{
          flex: 0 0 100%; scroll-snap-align: center;
          border-radius: var(--radius-lg); overflow: hidden; position: relative;
          aspect-ratio: 2.35/1; /* Cinematic widescreen */
          box-shadow: var(--shadow-md); cursor: pointer;
      }}
      @media (max-width: 768px) {{
          .hero-slider-container {{ padding: 0 15px; margin-bottom: 30px; }}
          .hero-slide {{ aspect-ratio: 16/9; border-radius: var(--radius-md); }}
      }}
      
      .hero-slide img {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s ease; }}
      .hero-slide:hover img {{ transform: scale(1.03); }}
      
      .slider-nav-dots {{
          display: flex; justify-content: center; gap: 8px; margin-top: -25px; 
          position: relative; z-index: 5; margin-bottom: 25px;
      }}
      .slider-dot {{
          width: 8px; height: 8px; background: rgba(0,0,0,0.2); border-radius: 50%; 
          transition: all 0.3s; cursor: pointer;
      }}
      .slider-dot.active {{ background: var(--primary); transform: scale(1.3); }}

      /* --- NAVIGATION --- */
      .category-nav-wrapper {{
          position: sticky; top: 15px; z-index: 90;
          display: flex; justify-content: center;
          padding: 0 15px; margin-bottom: 40px;
      }}
      .category-nav {{
          display: flex; gap: 8px; overflow-x: auto; 
          padding: 8px; border-radius: 100px;
          background: rgba(255, 255, 255, 0.9); 
          backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255,255,255,0.6);
          box-shadow: var(--shadow-md);
          scrollbar-width: none; max-width: 100%;
      }}
      .category-nav::-webkit-scrollbar {{ display: none; }}
      
      .category-nav a {{
          color: var(--nav-text); text-decoration: none; padding: 10px 24px; 
          border-radius: 50px; font-weight: 600; white-space: nowrap; font-size: 0.95rem;
          transition: all 0.3s var(--ease-out); border: 1px solid transparent;
      }}
      .category-nav a:hover {{ background: rgba(0,0,0,0.05); }}
      .category-nav a.active {{ 
          background: var(--primary); color: white; 
          box-shadow: 0 4px 15px color-mix(in srgb, var(--primary), transparent 60%);
          border-color: var(--primary);
      }}

      /* --- MAIN CONTENT (WIDE ADAPTIVE) --- */
      .container {{ 
          max-width: 1800px; 
          margin: 0 auto; 
          padding: 0 25px; 
      }}
      
      .category-section {{ margin-bottom: 60px; scroll-margin-top: 120px; }}
      .category-title {{ 
          font-size: 2rem; color: var(--text-main); margin-bottom: 30px; 
          font-weight: 800; display: flex; align-items: center; gap: 20px;
          letter-spacing: -0.03em;
      }}
      .category-title::after {{ 
          content: ''; height: 2px; background: var(--secondary); flex-grow: 1; opacity: 0.3; border-radius: 2px;
      }}

      /* --- PRODUCT GRID (ADAPTIVE) --- */
      .products-grid {{ 
          display: grid; 
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); 
          gap: 30px; 
      }}
      
      @media (min-width: 1200px) {{
          .products-grid {{ grid-template-columns: repeat(4, 1fr); }}
      }}
      @media (min-width: 1500px) {{
          .products-grid {{ grid-template-columns: repeat(5, 1fr); }}
      }}
      @media (min-width: 1800px) {{
          .products-grid {{ grid-template-columns: repeat(6, 1fr); }}
      }}

      /* --- PRODUCT CARD --- */
      .product-card {{
          background: var(--surface); border-radius: var(--radius-md);
          overflow: hidden; display: flex; flex-direction: column;
          box-shadow: var(--shadow-sm); border: 1px solid var(--border-light);
          transition: all 0.4s var(--ease-out);
          height: 100%; position: relative; cursor: pointer;
      }}
      .product-card:hover {{ 
          transform: translateY(-8px) scale(1.01); 
          box-shadow: var(--shadow-lg); 
          border-color: color-mix(in srgb, var(--primary), transparent 80%);
      }}

      .product-image-wrapper {{ 
          width: 100%; aspect-ratio: 4/3; overflow: hidden; 
          background: #f5f5f7; position: relative;
      }}
      .product-image {{ 
          width: 100%; height: 100%; object-fit: cover; 
          transition: transform 0.6s var(--ease-out); 
      }}
      .product-card:hover .product-image {{ transform: scale(1.1); }}

      .product-info {{ 
          padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; 
      }}
      .product-header {{ margin-bottom: 10px; }}
      
      .product-name {{ 
          font-family: var(--font-sans);
          font-size: 1.2rem; font-weight: 700; margin: 0 0 8px; 
          line-height: 1.3; color: var(--text-main); letter-spacing: -0.01em;
      }}
      
      .product-desc {{ 
          font-size: 0.9rem; color: #64748b; line-height: 1.5; margin-bottom: 15px; 
          display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
      }}

      .product-footer {{ 
          display: flex; justify-content: space-between; align-items: center; 
          margin-top: auto; padding-top: 15px; border-top: 1px solid var(--border-light);
      }}
      .product-price {{ font-size: 1.25rem; font-weight: 800; color: var(--text-main); }}
      
      .add-btn {{
          background: var(--primary); color: white; border: none;
          padding: 10px 20px; border-radius: var(--radius-sm);
          font-weight: 600; cursor: pointer; font-size: 0.95rem;
          display: flex; align-items: center; gap: 8px;
          transition: all 0.2s var(--ease-out); z-index: 2; position: relative;
      }}
      .add-btn:hover {{ background: color-mix(in srgb, var(--primary), black 15%); transform: translateY(-2px); box-shadow: 0 4px 12px color-mix(in srgb, var(--primary), transparent 60%); }}
      .add-btn:active {{ transform: scale(0.95); }}

      /* --- SHARE BUTTON & TOAST --- */
      .share-btn {{
          position: absolute; top: 20px; right: 70px;
          width: 40px; height: 40px; border-radius: 50%;
          background: #f8fafc; border: 1px solid #e2e8f0;
          color: var(--text-main); font-size: 1.1rem;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer; transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
          z-index: 10;
      }}
      .share-btn:hover {{
          background: var(--primary); color: white; border-color: var(--primary);
          transform: scale(1.1) rotate(15deg);
      }}
      
      /* Toast Notification */
      .toast {{
          position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%) translateY(100px);
          background: rgba(0,0,0,0.85); color: white; padding: 12px 24px;
          border-radius: 50px; font-size: 0.95rem; font-weight: 500;
          opacity: 0; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); z-index: 9999;
          display: flex; align-items: center; gap: 10px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.25); pointer-events: none;
      }}
      .toast.visible {{ transform: translateX(-50%) translateY(0); opacity: 1; }}

      /* --- MOBILE SPECIFIC OVERRIDES --- */
      @media (max-width: 768px) {{
          header {{ height: 35vh; min-height: 300px; border-radius: 0 0 30px 30px; margin-bottom: 20px; }}
          header h1 {{ font-size: 2.2rem; }}
          .header-logo {{ height: 70px; margin-bottom: 10px; }}
          
          .category-nav-wrapper {{ padding: 0 10px; top: 10px; margin-bottom: 25px; }}
          .category-nav {{ padding: 6px; gap: 5px; }}
          .category-nav a {{ padding: 8px 18px; font-size: 0.85rem; }}
          .category-title {{ font-size: 1.6rem; margin-bottom: 20px; }}
          
          .products-grid {{ 
              grid-template-columns: repeat(2, 1fr); 
              gap: 12px; padding: 0 5px;
          }}
          
          .product-info {{ padding: 12px; }}
          .product-name {{ font-size: 1rem; margin-bottom: 6px; }}
          .product-desc {{ font-size: 0.75rem; margin-bottom: 10px; -webkit-line-clamp: 2; }}
          .product-price {{ font-size: 1.1rem; }}
          .product-footer {{ padding-top: 10px; }}
          
          .add-btn {{ padding: 0; width: 36px; height: 36px; border-radius: 50%; justify-content: center; }}
          .add-btn span {{ display: none; }}
          .add-btn i {{ font-size: 1rem; }}
          
          .container {{ padding: 0 10px; }}
          .category-section {{ margin-bottom: 40px; }}
      }}

      /* --- FLOATING CART --- */
      #cart-toggle {{
          position: fixed; bottom: 30px; right: 30px; width: 70px; height: 70px;
          background: var(--primary); color: white; border-radius: 50%; border: none;
          box-shadow: var(--shadow-float); cursor: pointer; z-index: 99;
          display: flex; justify-content: center; align-items: center; 
          transition: transform 0.3s var(--ease-bounce);
      }}
      #cart-toggle:hover {{ transform: scale(1.1) rotate(5deg); }}
      #cart-toggle i {{ font-size: 1.8rem; }}
      #cart-count {{ 
          position: absolute; top: -2px; right: -2px; background: #ff3b30; color: white;
          width: 26px; height: 26px; border-radius: 50%; font-size: 0.85rem; font-weight: 800; 
          display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
          border: 2px solid white;
      }}
      
      @media (max-width: 768px) {{
          #cart-toggle {{ width: 60px; height: 60px; bottom: 25px; right: 20px; }}
          #cart-toggle i {{ font-size: 1.5rem; }}
      }}

      /* --- SIDEBAR (Cart) --- */
      #cart-sidebar {{
          position: fixed; top: 0; right: -100%; width: 100%; max-width: 450px; height: 100%;
          z-index: 1000; display: flex; flex-direction: column;
          transition: right 0.5s var(--ease-out);
          box-shadow: -10px 0 50px rgba(0,0,0,0.2);
      }}
      #cart-sidebar.open {{ right: 0; }}
      @media (max-width: 768px) {{ #cart-sidebar {{ max-width: 100%; }} }}
      
      .cart-content-wrapper {{
          height: 100%; display: flex; flex-direction: column;
          background: var(--surface-glass); 
          backdrop-filter: blur(30px); -webkit-backdrop-filter: blur(30px);
      }}
      
      .cart-header {{ 
          padding: 25px 30px; display: flex; justify-content: space-between; align-items: center; 
          background: rgba(255,255,255,0.5); border-bottom: 1px solid var(--border-light);
      }}
      .cart-header h3 {{ font-size: 1.5rem; font-weight: 800; }}
      
      .cart-items {{ flex-grow: 1; overflow-y: auto; padding: 25px; }}
      
      .cart-item {{ 
          display: flex; justify-content: space-between; align-items: center; 
          margin-bottom: 18px; padding: 18px; background: white; 
          border-radius: 16px; box-shadow: var(--shadow-sm);
          animation: fadeUp 0.3s ease; border: 1px solid transparent;
          transition: border 0.2s;
      }}
      .cart-item:hover {{ border-color: var(--primary); }}
      
      .cart-item-info {{ flex-grow: 1; padding-right: 15px; }}
      .cart-item-name {{ font-weight: 700; font-size: 1rem; display: block; margin-bottom: 5px; }}
      .cart-item-mods {{ font-size: 0.85rem; color: #888; display: block; }}
      .cart-item-price {{ color: var(--primary); font-weight: 800; font-size: 1rem; margin-top: 6px; display: block; }}
      
      .qty-control {{ display: flex; align-items: center; gap: 10px; background: #f1f5f9; padding: 5px; border-radius: 10px; }}
      .qty-btn {{ 
          width: 32px; height: 32px; background: white; border-radius: 8px; border: none; 
          cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700;
          box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: all 0.1s;
      }}
      .qty-btn:active {{ transform: scale(0.9); }}
      .qty-val {{ font-weight: 600; min-width: 20px; text-align: center; }}
      
      .cart-footer {{ padding: 30px; background: white; box-shadow: 0 -10px 40px rgba(0,0,0,0.05); }}
      .cart-total-row {{ display: flex; justify-content: space-between; font-size: 1.4rem; font-weight: 800; margin-bottom: 25px; color: var(--text-main); }}
      
      /* --- SECONDARY BUTTON --- */
      .secondary-btn {{
          width: 100%; padding: 12px; background: white; color: var(--text-main);
          border: 1px solid var(--border-light); border-radius: var(--radius-md);
          font-size: 0.95rem; font-weight: 600; cursor: pointer;
          transition: all 0.2s; display: flex; justify-content: center; align-items: center; gap: 8px;
          margin-bottom: 15px; box-shadow: var(--shadow-sm);
      }}
      .secondary-btn:hover {{ border-color: var(--primary); color: var(--primary); transform: translateY(-1px); }}

      .main-btn {{ 
          width: 100%; padding: 18px; background: var(--primary); color: white; 
          border: none; border-radius: var(--radius-md); font-size: 1.1rem; font-weight: 700; 
          cursor: pointer; transition: all 0.2s; display: flex; justify-content: center; align-items: center; gap: 12px;
          box-shadow: 0 8px 20px color-mix(in srgb, var(--primary), transparent 60%);
      }}
      .main-btn:hover {{ background: color-mix(in srgb, var(--primary), black 10%); transform: translateY(-2px); }}
      .main-btn:active {{ transform: scale(0.98); }}
      .main-btn:disabled {{ background: #e2e8f0; color: #94a3b8; cursor: not-allowed; box-shadow: none; transform: none; }}

      /* --- MODALS (General) --- */
      .modal-overlay {{
          position: fixed; top: 0; left: 0; width: 100%; height: 100%;
          background: rgba(0,0,0,0.6); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
          z-index: 2000; display: none; justify-content: center; align-items: center;
          opacity: 0; transition: opacity 0.3s ease;
      }}
      .modal-overlay.visible {{ display: flex; opacity: 1; }}
      
      .modal-content {{
          background: #fff; padding: 35px; border-radius: 28px; 
          width: 90%; max-width: 550px; max-height: 90vh; overflow-y: auto; 
          transform: scale(0.9) translateY(20px); opacity: 0; transition: all 0.4s var(--ease-bounce);
          box-shadow: var(--shadow-lg); position: relative;
      }}
      .modal-overlay.visible .modal-content {{ transform: scale(1) translateY(0); opacity: 1; }}
      
      @media (max-width: 768px) {{
          .modal-overlay {{ align-items: flex-end; }}
          .modal-content {{ 
              width: 100%; max-width: 100%; border-radius: 30px 30px 0 0; 
              padding: 25px; max-height: 85vh; transform: translateY(100%);
          }}
          .modal-overlay.visible .modal-content {{ transform: translateY(0); }}
      }}

      /* --- PRODUCT DETAILS MODAL --- */
      .product-detail-img {{ 
          width: 100%; aspect-ratio: 16/9; object-fit: cover; border-radius: 18px; margin-bottom: 20px; 
          box-shadow: var(--shadow-sm);
      }}
      .detail-title {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }}
      .detail-price {{ font-size: 1.5rem; color: var(--primary); font-weight: 800; margin-bottom: 20px; }}
      .detail-desc {{ color: #64748b; font-size: 1rem; line-height: 1.6; margin-bottom: 25px; }}

      /* --- MODIFIERS IN MODAL --- */
      #detail-modifiers {{
          margin-bottom: 30px;
          border-top: 1px solid #f1f5f9;
          padding-top: 15px;
      }}
      .mod-detail-item {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid #f1f5f9;
          cursor: pointer;
      }}
      .mod-detail-item label {{
          display: flex;
          align-items: center;
          width: 100%;
          cursor: pointer;
      }}
      .mod-detail-checkbox {{
          width: 22px; height: 22px; 
          margin-right: 15px; 
          accent-color: var(--primary);
          cursor: pointer;
      }}
      .mod-detail-name {{ font-weight: 600; font-size: 1rem; color: var(--text-main); flex-grow: 1; }}
      .mod-detail-price {{ font-weight: 700; color: var(--primary); font-size: 0.95rem; }}

      /* --- CHECKOUT FORM --- */
      .form-group {{ margin-bottom: 22px; }}
      .form-group label {{ display: block; margin-bottom: 8px; font-weight: 700; font-size: 0.9rem; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; }}
      
      .form-control {{ 
          width: 100%; padding: 16px; border: 2px solid #e2e8f0; border-radius: 14px; 
          font-size: 1rem; font-family: var(--font-sans); background: #f8fafc; transition: all 0.2s;
      }}
      .form-control:focus {{ outline: none; background: white; border-color: var(--primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary), transparent 90%); }}
      
      .radio-group {{ display: flex; gap: 12px; }}
      .radio-group label {{ 
          flex: 1; padding: 15px; text-align: center; cursor: pointer; 
          border-radius: 14px; border: 2px solid #f1f5f9; background: white;
          color: #64748b; font-weight: 600; transition: all 0.2s;
          display: flex; flex-direction: column; gap: 8px; font-size: 0.95rem;
      }}
      .radio-group input {{ display: none; }}
      .radio-group input:checked + label {{ 
          background: color-mix(in srgb, var(--primary), white 95%); 
          border-color: var(--primary); color: var(--primary); box-shadow: var(--shadow-sm); transform: translateY(-2px);
      }}
      .radio-group label i {{ font-size: 1.4rem; margin-bottom: 2px; }}

      /* --- SUCCESS MODAL STYLES --- */
      .success-checkmark {{
        font-size: 4rem; color: #22c55e; margin-bottom: 20px;
        animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      }}
      @keyframes popIn {{ 0% {{ transform: scale(0); opacity: 0; }} 100% {{ transform: scale(1); opacity: 1; }} }}
      
      /* --- ADDRESS SUGGESTIONS (OSM) --- */
      .suggestions-list {{
        position: absolute; background: white; width: 100%; 
        border: 1px solid #e2e8f0; border-radius: 0 0 14px 14px; 
        max-height: 200px; overflow-y: auto; z-index: 1000;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1); margin-top: -5px; display: none;
      }}
      .suggestion-item {{ 
        padding: 12px 16px; cursor: pointer; 
        border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; color: #334155;
      }}
      .suggestion-item:hover {{ background: #f8fafc; color: var(--primary); }}
      .suggestion-item:last-child {{ border-bottom: none; }}
      .suggestion-item i {{ margin-right: 8px; color: #94a3b8; }}

      /* --- FOOTER --- */
      footer {{ 
          background: var(--footer-bg); color: var(--footer-text); 
          padding: 80px 20px 40px; margin-top: auto; 
      }}
      .footer-content {{ 
          display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
          gap: 50px; max-width: 1200px; margin: 0 auto; 
      }}
      .footer-section h4 {{ 
          font-size: 1rem; margin-bottom: 25px; opacity: 0.7; 
          text-transform: uppercase; font-weight: 800; letter-spacing: 1.5px;
      }}
      .footer-link {{ 
          display: flex; align-items: center; gap: 12px; margin-bottom: 16px; 
          color: inherit; text-decoration: none; opacity: 0.85; transition: opacity 0.2s; font-size: 1.05rem;
      }}
      .footer-link:hover {{ opacity: 1; }}
      .footer-link i {{ width: 20px; text-align: center; }}
      
      .social-links {{ display: flex; gap: 15px; }}
      .social-links a {{ 
          display: flex; width: 45px; height: 45px; border-radius: 12px; 
          background: rgba(255,255,255,0.15); align-items: center; justify-content: center; 
          color: white; text-decoration: none; transition: all 0.3s;
          font-size: 1.3rem;
      }}
      .social-links a:hover {{ background: var(--primary); transform: translateY(-3px); }}

      /* --- ANIMATIONS & UTILS --- */
      @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
      @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
      .spinner {{ 
          border: 3px solid rgba(0,0,0,0.1); border-top: 3px solid var(--primary); 
          border-radius: 50%; width: 24px; height: 24px; animation: spin 0.8s linear infinite; 
      }}
      
      .page-content-body img {{ max-width: 100%; border-radius: 12px; margin: 10px 0; }}
      .page-content-body h1, .page-content-body h2 {{ color: var(--primary); margin-top: 15px; }}

      /* --- FREE DELIVERY PROGRESS BAR --- */
      .free-delivery-widget {{
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 1px dashed var(--border-light);
      }}
      .fd-text {{
          font-size: 0.9rem;
          color: #64748b;
          font-weight: 600;
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
      }}
      .fd-progress-bg {{
          height: 8px;
          background: #f1f5f9;
          border-radius: 10px;
          overflow: hidden;
          position: relative;
      }}
      .fd-progress-fill {{
          height: 100%;
          background: var(--primary);
          width: 0%;
          border-radius: 10px;
          transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.3s;
          box-shadow: 0 2px 5px color-mix(in srgb, var(--primary), transparent 60%);
      }}
      .fd-progress-fill.completed {{
          background: #22c55e; /* Green success color */
          box-shadow: 0 2px 5px rgba(34, 197, 94, 0.4);
      }}
      .fd-icon {{
          color: var(--primary);
          margin-right: 6px;
      }}
    </style>
</head>
<body>
    <header>
        <div class="header-bg"></div>
        <div class="header-content">
            <div class="header-logo-container">{logo_html}</div>
            
            <h1>{site_header_text}</h1>
            
            <div class="header-info-actions">
                <a href="https://maps.google.com/?q={footer_address}" target="_blank" class="header-address">
                    <i class="fa-solid fa-location-dot"></i> {footer_address}
                </a>
                
                <a href="tel:{footer_phone}" class="header-book-btn">
                    <i class="fa-solid fa-chair"></i> Забронювати столик
                </a>
            </div>
            </div>
    </header>
    
    {banners_html}
    
    <div class="category-nav-wrapper">
        <nav class="category-nav" id="category-nav">{server_rendered_nav}</nav>
    </div>
    
    <div class="container">
        <main id="menu">{server_rendered_menu}</main>
    </div>

    <button id="cart-toggle">
        <i class="fa-solid fa-bag-shopping"></i>
        <span id="cart-count">0</span>
    </button>

    <aside id="cart-sidebar">
        <div class="cart-content-wrapper">
            <div class="cart-header">
                <h3 style="margin:0;">Ваше замовлення</h3>
                <button id="close-cart-btn" style="background:none; border:none; font-size:1.8rem; cursor:pointer; color: #94a3b8; transition: color 0.2s;">×</button>
            </div>
            <div id="cart-items-container" class="cart-items"></div>
            <div class="cart-footer">
                
                <div id="free-delivery-widget" class="free-delivery-widget" style="display: none;">
                    <div class="fd-text">
                        <span id="fd-message">До безкоштовної доставки:</span>
                        <span id="fd-amount" style="color: var(--text-main);">0 грн</span>
                    </div>
                    <div class="fd-progress-bg">
                        <div id="fd-bar" class="fd-progress-fill"></div>
                    </div>
                </div>
                
                <div class="cart-total-row" style="font-size: 0.9rem; color: #666; margin-bottom: 5px;">
                    <span>Доставка:</span>
                    <span id="cart-delivery-cost">0.00 грн</span>
                </div>
                
                <div class="cart-total-row">
                    <span>Разом:</span>
                    <span id="cart-total-price">0.00 грн</span>
                </div>

                <button id="open-zones-btn" class="secondary-btn">
                    <i class="fa-solid fa-map-location-dot"></i> Зони доставки
                </button>

                <button id="checkout-btn" class="main-btn" disabled>
                    <span>Оформити замовлення</span> <i class="fa-solid fa-arrow-right"></i>
                </button>
            </div>
        </div>
    </aside>

    <div id="zones-modal" class="modal-overlay">
        <div class="modal-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:15px; border-bottom:1px solid #f1f5f9;">
                <h3 style="margin:0; font-size:1.5rem;">Зони доставки</h3>
                <span class="close-modal" style="font-size:1.8rem; cursor:pointer; color:#cbd5e1;">×</span>
            </div>
            <div class="page-content-body" style="line-height:1.7; color:#334155; font-size: 1.05rem;">
                {delivery_zones_content}
            </div>
        </div>
    </div>

    <div id="product-modal" class="modal-overlay">
        <div class="modal-content">
            <button id="detail-share-btn" class="share-btn" title="Поділитися">
                <i class="fa-solid fa-share-nodes"></i>
            </button>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; position: absolute; top: 20px; right: 20px; z-index: 10;">
                <span class="close-modal" style="font-size:2rem; cursor:pointer; color:#333; background: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">×</span>
            </div>
            <img src="" id="detail-img" class="product-detail-img">
            <div class="detail-title" id="detail-name"></div>
            <div class="detail-price" id="detail-price"></div>
            <div class="detail-desc" id="detail-desc"></div>
            
            <div id="detail-modifiers"></div>
            
            <button id="detail-add-btn" class="main-btn">
                <span>В кошик</span> <i class="fa-solid fa-plus"></i>
            </button>
        </div>
    </div>

    <div id="checkout-modal" class="modal-overlay">
        <div class="modal-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:30px; padding-bottom: 15px; border-bottom: 1px solid #f1f5f9;">
                <h3 style="font-size:1.6rem; margin:0;">Оформлення</h3>
                <span class="close-modal" style="font-size:1.8rem; cursor:pointer; color:#cbd5e1;">×</span>
            </div>
            
            <form id="checkout-form">
                <div class="form-group">
                    <label>Отримання</label>
                    <div class="radio-group">
                        <input type="radio" id="delivery" name="delivery_type" value="delivery" checked>
                        <label for="delivery"><i class="fa-solid fa-motorcycle"></i> Доставка</label>
                        <input type="radio" id="pickup" name="delivery_type" value="pickup">
                        <label for="pickup"><i class="fa-solid fa-shop"></i> Самовивіз</label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Контакти</label>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                        <input type="text" id="customer_name" class="form-control" placeholder="Ваше ім'я" required>
                        <input type="tel" id="phone_number" class="form-control" placeholder="+380" maxlength="13" required>
                    </div>
                </div>
                
                <div id="address-group" class="form-group">
                    <label>Адреса</label>
                    <div style="position: relative;">
                        <input type="text" id="address" class="form-control" placeholder="Почніть вводити вулицю..." required autocomplete="off">
                        <div id="address-suggestions" class="suggestions-list"></div>
                    </div>
                </div>

                <div class="form-group">
                    <label>Час</label>
                    <div class="radio-group">
                        <input type="radio" id="asap" name="delivery_time" value="asap" checked>
                        <label for="asap"><i class="fa-solid fa-fire"></i> Зараз</label>
                        <input type="radio" id="specific" name="delivery_time" value="specific">
                        <label for="specific"><i class="fa-regular fa-clock"></i> На час</label>
                    </div>
                </div>
                <div id="specific-time-group" class="form-group" style="display:none;">
                    <input type="text" id="specific_time_input" class="form-control" placeholder="Наприклад: 19:00">
                </div>

                <div class="form-group">
                    <label>Коментар до замовлення <span style="font-weight:normal; text-transform:none; color:#94a3b8; font-size:0.85em;">(необов'язково)</span></label>
                    <textarea id="order_comment" class="form-control" rows="2" placeholder="Наприклад: код домофону, не дзвонити у двері, потрібна решта з 500..." style="resize: vertical; min-height: 60px;"></textarea>
                </div>
                <div class="form-group">
                    <label>Оплата</label>
                    <div class="radio-group">
                        <input type="radio" id="pay_cash" name="payment_method" value="cash" checked>
                        <label for="pay_cash"><i class="fa-solid fa-money-bill-wave"></i> Готівка</label>
                        <input type="radio" id="pay_card" name="payment_method" value="card">
                        <label for="pay_card"><i class="fa-regular fa-credit-card"></i> Картка</label>
                    </div>
                </div>

                <div style="background: #f8fafc; padding: 15px; border-radius: 12px; margin-top: 20px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span>Сума замовлення:</span>
                        <span id="checkout-subtotal">0.00 грн</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px; color:#64748b;">
                        <span>Доставка:</span>
                        <span id="checkout-delivery">0.00 грн</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-weight:800; font-size:1.2rem; margin-top:10px; border-top:1px dashed #cbd5e1; padding-top:10px;">
                        <span>Разом до сплати:</span>
                        <span id="checkout-total">0.00 грн</span>
                    </div>
                </div>

                <button type="submit" id="place-order-submit" class="main-btn" style="margin-top:20px;">
                    Підтвердити замовлення
                </button>
            </form>
        </div>
    </div>
    
    <div id="success-modal" class="modal-overlay">
        <div class="modal-content" style="text-align: center; max-width: 400px; padding: 40px 30px;">
            <div class="success-checkmark"><i class="fa-solid fa-circle-check"></i></div>
            <h3 style="font-size: 1.8rem; margin-bottom: 10px; color: var(--text-main);">Замовлення прийнято!</h3>
            <p style="color: #64748b; margin-bottom: 25px; line-height: 1.6; font-size: 1.05rem;">
                Дякуємо, що обрали нас.<br>
                Наш оператор зв'яжеться з вами найближчим часом для підтвердження деталей.
            </p>
            <button onclick="window.location.reload()" class="main-btn" style="justify-content: center;">
                Чудово!
            </button>
        </div>
    </div>

    <div id="page-modal" class="modal-overlay">
        <div class="modal-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:15px; border-bottom:1px solid #f1f5f9;">
                <h3 id="page-modal-title" style="margin:0; font-size:1.5rem;"></h3>
                <span class="close-modal" style="font-size:1.8rem; cursor:pointer; color:#cbd5e1;">×</span>
            </div>
            <div id="page-modal-body" class="page-content-body" style="line-height:1.7; color:#334155; font-size: 1.05rem;"></div>
        </div>
    </div>

    <div id="marketing-popup" class="modal-overlay" style="z-index: 9999;">
        <div class="modal-content" style="text-align: center; padding: 0; overflow: hidden; max-width: 400px;">
            <div style="position: relative;">
                <button onclick="closeMarketingPopup()" style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.5); color: white; border: none; width: 30px; height: 30px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; line-height: 1;">×</button>
                <img id="popup-img" src="" style="width: 100%; display: none; object-fit: cover;">
            </div>
            <div style="padding: 25px;">
                <h3 id="popup-title" style="margin-bottom: 10px; font-size: 1.5rem;"></h3>
                <p id="popup-content" style="color: #64748b; margin-bottom: 20px; font-size: 1rem;"></p>
                <a id="popup-btn" href="#" class="main-btn" style="text-decoration: none; justify-content: center; display: none;"></a>
            </div>
        </div>
    </div>
    
    <div id="toast-notification" class="toast">
        <i class="fa-solid fa-check-circle" style="color: #4ade80;"></i>
        <span>Посилання скопійовано!</span>
    </div>

    <footer>
        <div class="footer-content">
            <div class="footer-section">
                <h4>Контакти</h4>
                <a href="#" class="footer-link"><i class="fa-solid fa-location-dot"></i> <span>{footer_address}</span></a>
                <a href="tel:{footer_phone}" class="footer-link"><i class="fa-solid fa-phone"></i> <span>{footer_phone}</span></a>
                <div class="footer-link"><i class="fa-regular fa-clock"></i> <span>{working_hours}</span></div>
            </div>
            <div class="footer-section">
                <h4>Інформація</h4>
                <div class="menu-pages-links">
                    {menu_links_html}
                </div>
            </div>
            <div class="footer-section">
                <h4>Ми в соцмережах</h4>
                <div class="social-links">{social_links_html}</div>
            </div>
        </div>
        <div style="text-align:center; margin-top:60px; opacity:0.4; font-size:0.85rem;">
            © 2026 {site_title}. All rights reserved.
        </div>
    </footer>

    <script>
        // NEW: Global Settings from Server
        const DELIVERY_COST = {delivery_cost_val};
        const FREE_DELIVERY_FROM = {free_delivery_from_val}; // null or number
        const SEO_TEMPLATES = {seo_templates_json}; // <--- ЗАВАНТАЖЕННЯ ШАБЛОНІВ
        
        // --- GOOGLE ANALYTICS & ADS SETTINGS ---
        // Отримуємо ID з сервера
        const GA_ID = "{google_analytics_id}"; 
        const ADS_ID = "{google_ads_id}";                 // <-- НОВОЕ (Google Ads Conversion ID)
        const ADS_LABEL = "{google_ads_conversion_label}"; // <-- НОВОЕ (Google Ads Conversion Label)

        // Функція ініціалізації
        function initGA() {{
            // Завантажуємо скрипт, якщо є ID Аналітики АБО ID Реклами
            const targetID = (GA_ID && GA_ID !== "None" && GA_ID.length > 5) ? GA_ID : 
                             ((ADS_ID && ADS_ID !== "None" && ADS_ID.length > 5) ? ADS_ID : null);

            if (targetID) {{
                const script = document.createElement('script');
                script.async = true;
                script.src = `https://www.googletagmanager.com/gtag/js?id=${{targetID}}`;
                document.head.appendChild(script);

                window.dataLayer = window.dataLayer || [];
                function gtag(){{dataLayer.push(arguments);}}
                window.gtag = gtag;
                gtag('js', new Date());

                // Config Analytics (якщо є)
                if (GA_ID && GA_ID !== "None") {{
                    gtag('config', GA_ID);
                }}
                
                // Config Google Ads (напряму, якщо є)
                if (ADS_ID && ADS_ID !== "None") {{
                    gtag('config', ADS_ID);
                    console.log("Google Ads Initialized: " + ADS_ID);
                }}
            }}
        }}

        // Функція відправки подій в Аналітику (загальна)
        function sendGA(eventName, params) {{
            if (window.gtag) {{
                window.gtag('event', eventName, params);
            }}
        }}
        
        // --- НОВА ФУНКЦІЯ: ВІДПРАВКА КОНВЕРСІЇ В GOOGLE ADS ---
        function sendAdsConversion(value, transactionId) {{
            if (window.gtag && ADS_ID && ADS_ID !== "None" && ADS_LABEL && ADS_LABEL !== "None") {{
                window.gtag('event', 'conversion', {{
                    'send_to': ADS_ID + '/' + ADS_LABEL,
                    'value': value,
                    'currency': 'UAH',
                    'transaction_id': transactionId
                }});
                console.log("Ads Conversion Sent directly to: " + ADS_ID + '/' + ADS_LABEL);
            }}
        }}
        
        // --- TRANSLITERATION & UTILS ---
        function transliterate(word) {{
            const converter = {{
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye', 
                'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l', 
                'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 
                'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 
                'ю': 'yu', 'я': 'ya', ' ': '-', "'": '', '’': ''
            }};
            
            return word.toLowerCase().split('').map(char => {{
                return converter[char] || (/[a-z0-9\-]/.test(char) ? char : '');
            }}).join('').replace(/-+/g, '-').replace(/^-|-$/g, '');
        }}
        
        function slugify(text) {{
            return transliterate(text);
        }}
        
        function showToast(msg) {{
            const toast = document.getElementById('toast-notification');
            toast.querySelector('span').innerText = msg;
            toast.classList.add('visible');
            setTimeout(() => toast.classList.remove('visible'), 3000);
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            // Запускаємо аналітику та рекламу
            initGA();
            
            // --- HERO SLIDER LOGIC ---
            const slider = document.querySelector('.hero-slider');
            if (slider) {{
                let isDown = false;
                let startX, scrollLeft;
                const dots = document.querySelectorAll('.slider-dot');
                
                // Touch/Mouse Drag support
                slider.addEventListener('mousedown', (e) => {{ isDown = true; slider.classList.add('active'); startX = e.pageX - slider.offsetLeft; scrollLeft = slider.scrollLeft; }});
                slider.addEventListener('mouseleave', () => {{ isDown = false; slider.classList.remove('active'); }});
                slider.addEventListener('mouseup', () => {{ isDown = false; slider.classList.remove('active'); }});
                slider.addEventListener('mousemove', (e) => {{ if(!isDown) return; e.preventDefault(); const x = e.pageX - slider.offsetLeft; const walk = (x - startX) * 2; slider.scrollLeft = scrollLeft - walk; }});

                // Mobile touch pause
                slider.addEventListener('touchstart', () => clearInterval(scrollInterval));
                slider.addEventListener('touchend', () => startAutoScroll());

                // Auto Scroll
                let scrollInterval;
                function startAutoScroll() {{
                    clearInterval(scrollInterval);
                    scrollInterval = setInterval(() => {{
                        if(slider.scrollWidth - slider.scrollLeft <= slider.clientWidth + 5) {{
                            slider.scrollTo({{left: 0, behavior: 'smooth'}});
                        }} else {{
                            slider.scrollBy({{left: slider.clientWidth, behavior: 'smooth'}});
                        }}
                    }}, 5000); // 5 sec
                }}
                startAutoScroll();

                // Update dots on scroll
                slider.addEventListener('scroll', () => {{
                    const index = Math.round(slider.scrollLeft / slider.clientWidth);
                    dots.forEach(d => d.classList.remove('active'));
                    if(dots[index]) dots[index].classList.add('active');
                }});
                
                // Pause on hover
                slider.addEventListener('mouseenter', () => clearInterval(scrollInterval));
                slider.addEventListener('mouseleave', () => startAutoScroll());
            }}

            // --- MARKETING POPUP LOGIC ---
            const popupData = {popup_data_json}; 
            
            if (popupData && popupData.is_active) {{
                const popupEl = document.getElementById('marketing-popup');
                const storageKey = 'viewed_popup_' + popupData.id;
                const alreadyViewed = localStorage.getItem(storageKey);
                
                if (!popupData.show_once || !alreadyViewed) {{
                    if (popupData.image_url) {{
                        const img = document.getElementById('popup-img');
                        img.src = '/' + popupData.image_url;
                        img.style.display = 'block';
                    }}
                    
                    if (popupData.title) document.getElementById('popup-title').innerText = popupData.title;
                    if (popupData.content) document.getElementById('popup-content').innerText = popupData.content;
                    
                    if (popupData.button_text && popupData.button_link) {{
                        const btn = document.getElementById('popup-btn');
                        btn.innerText = popupData.button_text;
                        btn.href = popupData.button_link;
                        btn.style.display = 'flex';
			btn.onclick = function() {{
                            closeMarketingPopup();
                        }};
                    }}
                    
                    setTimeout(() => {{
                        popupEl.classList.add('visible');
                    }}, 1500);
                    
                    if (popupData.show_once) {{
                        localStorage.setItem(storageKey, 'true');
                    }}
                }}
            }}
            
            window.closeMarketingPopup = () => {{
                document.getElementById('marketing-popup').classList.remove('visible');
            }};
            // -----------------------------

            let cart = JSON.parse(localStorage.getItem('webCart') || '{{}}');
            let menuData = null;
            // Для модального окна деталей
            let currentDetailProduct = null;

            // DOM Elements
            const menuContainer = document.getElementById('menu');
            const cartSidebar = document.getElementById('cart-sidebar');
            const cartItemsContainer = document.getElementById('cart-items-container');
            const cartTotalEl = document.getElementById('cart-total-price');
            const cartCountEl = document.getElementById('cart-count');
            const checkoutBtn = document.getElementById('checkout-btn');
            
            // Product Detail Elements
            const productModal = document.getElementById('product-modal');
            const detailImg = document.getElementById('detail-img');
            const detailName = document.getElementById('detail-name');
            const detailPrice = document.getElementById('detail-price');
            const detailDesc = document.getElementById('detail-desc');
            const detailModifiers = document.getElementById('detail-modifiers');
            const detailAddBtn = document.getElementById('detail-add-btn');

            fetchMenu();

            async function fetchMenu() {{
                try {{
                    const res = await fetch('/api/menu');
                    if (!res.ok) throw new Error("Failed");
                    menuData = await res.json();
                    
                    // Pre-process slugs for lookups
                    menuData.products.forEach(p => {{
                        p.slug = slugify(p.name);
                    }});
                    
                    renderMenu();
                    updateCartView();
                    
                    // --- URL CHECK FOR DEEP LINKING ---
                    const urlParams = new URLSearchParams(window.location.search);
                    const prodSlug = urlParams.get('p');
                    if (prodSlug) {{
                        const productToOpen = menuData.products.find(p => p.slug === prodSlug || p.id == prodSlug);
                        if (productToOpen) {{
                            openProductDetails(productToOpen);
                        }}
                    }}
                    // ----------------------------------
                    
                }} catch (e) {{
                    menuContainer.innerHTML = '<div style="text-align:center; padding:60px; color:#94a3b8;">Не вдалося завантажити меню.</div>';
                }}
            }}

            function renderMenu() {{
                menuContainer.innerHTML = '';
                const nav = document.getElementById('category-nav');
                nav.innerHTML = '';

                menuData.categories.forEach((cat, idx) => {{
                    const link = document.createElement('a');
                    link.href = `#cat-${{cat.id}}`;
                    link.textContent = cat.name;
                    if(idx===0) link.classList.add('active');
                    nav.appendChild(link);

                    const section = document.createElement('div');
                    section.id = `cat-${{cat.id}}`;
                    section.className = 'category-section';
                    section.innerHTML = `<h2 class="category-title">${{cat.name}}</h2>`;

                    const grid = document.createElement('div');
                    grid.className = 'products-grid';

                    const products = menuData.products.filter(p => p.category_id === cat.id);
                    if (products.length > 0) {{
                        products.forEach(prod => {{
                            const card = document.createElement('div');
                            card.className = 'product-card';
                            const img = prod.image_url ? `/${{prod.image_url}}` : '/static/images/placeholder.jpg';
                            
                            // *** FIXED LINE HERE ***
                            // Correctly replace quotes with " for HTML attribute
                            const prodJson = JSON.stringify(prod).replace(/"/g, '&quot;');
                            
                            // Клик по карточке открывает детали
                            card.onclick = (e) => {{
                                if(!e.target.closest('.add-btn')) openProductDetails(prod);
                            }};

                            // UPDATE FOR SEO: h3 tag and alt attribute
                            card.innerHTML = `
                                <div class="product-image-wrapper"><img src="${{img}}" alt="${{prod.name}}" class="product-image" loading="lazy"></div>
                                <div class="product-info">
                                    <div class="product-header">
                                        <h3 class="product-name">${{prod.name}}</h3>
                                        <div class="product-desc">${{prod.description || ''}}</div>
                                    </div>
                                    <div class="product-footer">
                                        <div class="product-price">${{prod.price}} грн</div>
                                        <button class="add-btn" data-product="${{prodJson}}" onclick="event.stopPropagation(); handleAddClick(this)">
                                            <span>Додати</span> <i class="fa-solid fa-plus"></i>
                                        </button>
                                    </div>
                                </div>
                            `;
                            grid.appendChild(card);
                        }});
                        section.appendChild(grid);
                        menuContainer.appendChild(section);
                    }}
                }});
                setupScrollSpy();
            }}

            // Логика клика по кнопке "Добавить" в списке
            window.handleAddClick = (btn) => {{
                const prod = JSON.parse(btn.dataset.product);
                
                // Если у товара есть модификаторы, обязательно открываем карточку
                if (prod.modifiers && prod.modifiers.length > 0) {{
                    openProductDetails(prod);
                }} else {{
                    // Анимация кнопки
                    const originalHTML = btn.innerHTML;
                    btn.classList.add('added');
                    btn.innerHTML = '<i class="fa-solid fa-check"></i>';
                    setTimeout(() => {{ 
                        btn.classList.remove('added'); 
                        btn.innerHTML = originalHTML;
                    }}, 1000);
                    
                    addToCart(prod, []);
                }}
            }};
            
            // --- SEO & SHARE LOGIC ---
            function updateProductSEO(prod) {{
                // Удаляем старую разметку
                const oldScript = document.getElementById('json-ld-product');
                if (oldScript) oldScript.remove();

                const script = document.createElement('script');
                script.id = 'json-ld-product';
                script.type = 'application/ld+json';
                
                const siteUrl = window.location.origin;
                const imgUrl = prod.image_url ? `${{siteUrl}}/${{prod.image_url}}` : `${{siteUrl}}/static/images/placeholder.jpg`;
                const productUrl = `${{siteUrl}}?p=${{prod.slug}}`;

                const schema = {{
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": prod.name,
                    "image": [imgUrl],
                    "description": prod.description || prod.name,
                    "sku": prod.id,
                    "offers": {{
                        "@type": "Offer",
                        "url": productUrl,
                        "priceCurrency": "UAH",
                        "price": prod.price,
                        "availability": "https://schema.org/InStock"
                    }}
                }};

                script.textContent = JSON.stringify(schema);
                document.head.appendChild(script);
            }}

            async function shareProduct(prod) {{
                const url = `${{window.location.origin}}?p=${{prod.slug}}`;
                const shareData = {{
                    title: prod.name,
                    text: `Скуштуйте ${{prod.name}} у ${{document.title}}!`,
                    url: url
                }};

                if (navigator.share) {{
                    try {{
                        await navigator.share(shareData);
                    }} catch (err) {{}}
                }} else {{
                    try {{
                        await navigator.clipboard.writeText(url);
                        showToast('Посилання скопійовано!');
                    }} catch (err) {{
                        showToast('Не вдалося скопіювати');
                    }}
                }}
            }}

            // Логика открытия модального окна товара
            function openProductDetails(prod) {{
                currentDetailProduct = prod;
                detailImg.src = prod.image_url ? `/${{prod.image_url}}` : '/static/images/placeholder.jpg';
                detailName.textContent = prod.name;
                detailDesc.textContent = prod.description || 'Немає опису';
                
                // --- UPDATE URL & SEO ---
                if (!prod.slug) prod.slug = slugify(prod.name);
                const newUrl = `?p=${{prod.slug}}`;
                window.history.pushState({{path: newUrl}}, '', newUrl);
                
                // --- НОВА ЛОГІКА: ЗАСТОСУВАННЯ SEO ШАБЛОНІВ ---
                if (typeof SEO_TEMPLATES !== 'undefined' && SEO_TEMPLATES) {{
                    let newTitle = SEO_TEMPLATES.title_mask;
                    let newDesc = SEO_TEMPLATES.desc_mask;
                    
                    const replacements = {{
                        '{{name}}': prod.name,
                        '{{price}}': prod.price.toFixed(2),
                        '{{description}}': (prod.description || '').replace(/"/g, ''),
                        '{{site_title}}': SEO_TEMPLATES.site_title,
                        '{{category}}': prod.category_name || ''
                    }};

                    for (const [key, val] of Object.entries(replacements)) {{
                        newTitle = newTitle.split(key).join(val);
                        newDesc = newDesc.split(key).join(val);
                    }}

                    document.title = newTitle;
                    let metaDesc = document.querySelector('meta[name="description"]');
                    if (metaDesc) metaDesc.setAttribute('content', newDesc);
                }}
                
                updateProductSEO(prod);

                // --- GA EVENT: view_item ---
                sendGA('view_item', {{
                    currency: 'UAH',
                    value: prod.price,
                    items: [{{
                        item_id: prod.id.toString(),
                        item_name: prod.name,
                        price: prod.price,
                        quantity: 1
                    }}]
                }});
                // ---------------------------
                
                // Setup Share Btn
                const shareBtn = document.getElementById('detail-share-btn');
                shareBtn.onclick = () => shareProduct(prod);
                // ------------------------
                
                // Очистка и генерация модификаторов
                detailModifiers.innerHTML = '';
                
                if (prod.modifiers && prod.modifiers.length > 0) {{
                    const title = document.createElement('p');
                    title.textContent = "Добавки:";
                    title.style.cssText = "font-weight:600; color:#64748b; margin-bottom:10px;";
                    detailModifiers.appendChild(title);

                    prod.modifiers.forEach(mod => {{
                        const div = document.createElement('div');
                        div.className = 'mod-detail-item';
                        div.innerHTML = `
                            <label>
                                <input type="checkbox" class="mod-detail-checkbox" value="${{mod.id}}" data-price="${{mod.price}}" data-name="${{mod.name}}" onchange="updateDetailPrice()">
                                <span class="mod-detail-name">${{mod.name}}</span>
                                <span class="mod-detail-price">+${{mod.price}} грн</span>
                            </label>
                        `;
                        detailModifiers.appendChild(div);
                    }});
                }}
                
                updateDetailPrice(); // Установить начальную цену
                
                // Клик по кнопке "В корзину" внутри модалки
                detailAddBtn.onclick = () => {{
                    const selectedMods = [];
                    // Собираем выбранные чекбоксы
                    detailModifiers.querySelectorAll('.mod-detail-checkbox:checked').forEach(cb => {{
                        selectedMods.push({{
                            id: parseInt(cb.value),
                            name: cb.dataset.name,
                            price: parseFloat(cb.dataset.price)
                        }});
                    }});
                    
                    addToCart(currentDetailProduct, selectedMods);
                    productModal.classList.remove('visible');
                    
                    // Restore URL
                    window.history.pushState({{}}, '', window.location.pathname);
                    // НОВЕ: Повертаємо заголовок
                    if (typeof SEO_TEMPLATES !== 'undefined') {{
                        document.title = SEO_TEMPLATES.site_title;
                    }}
                }};
                
                productModal.classList.add('visible');
            }}
            
            // Функция обновления цены в модальном окне при выборе модификаторов
            window.updateDetailPrice = () => {{
                if (!currentDetailProduct) return;
                let price = currentDetailProduct.price;
                
                const checkedBoxes = detailModifiers.querySelectorAll('.mod-detail-checkbox:checked');
                checkedBoxes.forEach(cb => {{
                    price += parseFloat(cb.dataset.price);
                }});
                
                detailPrice.textContent = price.toFixed(2) + ' грн';
                // Обновляем текст на кнопке для наглядности
                const btnSpan = detailAddBtn.querySelector('span');
                if(btnSpan) btnSpan.textContent = `В кошик за ${{price.toFixed(2)}} грн`;
            }};

            function addToCart(prod, mods) {{
                const modIds = mods.map(m => m.id).sort().join('-');
                const key = `${{prod.id}}-${{modIds}}`;
                
                if (cart[key]) {{
                    cart[key].quantity++;
                }} else {{
                    let price = prod.price;
                    mods.forEach(m => price += m.price);
                    cart[key] = {{
                        id: prod.id, name: prod.name, price: price, quantity: 1, modifiers: mods, key: key
                    }};
                }}
                saveCart();
                updateCartView();
                
                const toggle = document.getElementById('cart-toggle');
                toggle.style.transform = 'scale(1.15) rotate(10deg)';
                setTimeout(() => toggle.style.transform = 'scale(1) rotate(0)', 300);

                // --- GA EVENT: add_to_cart ---
                let finalPrice = prod.price;
                mods.forEach(m => finalPrice += m.price);
                
                sendGA('add_to_cart', {{
                    currency: 'UAH',
                    value: finalPrice,
                    items: [{{
                        item_id: prod.id.toString(),
                        item_name: prod.name,
                        price: finalPrice,
                        quantity: 1,
                        item_variant: mods.map(m => m.name).join(', ')
                    }}]
                }});
                // -----------------------------
            }}

            function updateCartView() {{
                cartItemsContainer.innerHTML = '';
                let total = 0;
                let count = 0;
                const items = Object.values(cart);
                
                if (items.length === 0) {{
                    cartItemsContainer.innerHTML = '<div style="text-align:center;color:#94a3b8;margin-top:80px;"><i class="fa-solid fa-basket-shopping" style="font-size:3rem; opacity:0.2; margin-bottom:15px;"></i><p>Кошик порожній</p></div>';
                }}

                items.forEach(item => {{
                    total += item.price * item.quantity;
                    count += item.quantity;
                    
                    const div = document.createElement('div');
                    div.className = 'cart-item';
                    const modStr = (item.modifiers || []).map(m => m.name).join(', ');
                    
                    div.innerHTML = `
                        <div class="cart-item-info">
                            <span class="cart-item-name">${{item.name}}</span>
                            ${{modStr ? `<span class="cart-item-mods">+ ${{modStr}}</span>` : ''}}
                            <span class="cart-item-price">${{item.price}} грн</span>
                        </div>
                        <div class="qty-control">
                            <button class="qty-btn" onclick="updateQty('${{item.key}}', -1)">-</button>
                            <div class="qty-val">${{item.quantity}}</div>
                            <button class="qty-btn" onclick="updateQty('${{item.key}}', 1)">+</button>
                        </div>
                    `;
                    cartItemsContainer.appendChild(div);
                }});
                
                // --- LOGIC: Delivery Progress Bar ---
                const fdWidget = document.getElementById('free-delivery-widget');
                const fdMessage = document.getElementById('fd-message');
                const fdAmount = document.getElementById('fd-amount');
                const fdBar = document.getElementById('fd-bar');
                const deliveryCostEl = document.getElementById('cart-delivery-cost');
                
                let finalDelivery = DELIVERY_COST;

                // Проверяем, включена ли опция бесплатной доставки в админке
                if (FREE_DELIVERY_FROM !== null && FREE_DELIVERY_FROM > 0) {{
                    fdWidget.style.display = 'block';
                    
                    const remaining = FREE_DELIVERY_FROM - total;
                    let percent = (total / FREE_DELIVERY_FROM) * 100;
                    if (percent > 100) percent = 100;
                    
                    fdBar.style.width = `${{percent}}%`;

                    if (remaining > 0) {{
                        // Еще не набрали сумму
                        fdMessage.innerHTML = '<i class="fa-solid fa-truck-fast fd-icon"></i> До безкоштовної доставки:';
                        fdAmount.innerText = remaining.toFixed(0) + ' грн'; // Округляем до целых для красоты
                        fdAmount.style.color = 'var(--text-main)';
                        fdBar.classList.remove('completed');
                        finalDelivery = DELIVERY_COST;
                        
                        if(deliveryCostEl) deliveryCostEl.innerText = finalDelivery.toFixed(2) + ' грн';
                    }} else {{
                        // УРА! Бесплатная доставка
                        fdMessage.innerHTML = '<i class="fa-solid fa-gift fd-icon" style="color:#22c55e"></i> Доставка безкоштовна!';
                        fdAmount.innerText = ''; // Скрываем сумму, так как цель достигнута
                        fdBar.classList.add('completed');
                        finalDelivery = 0;
                        
                        if(deliveryCostEl) deliveryCostEl.innerHTML = '<span style="color:#22c55e">Безкоштовно</span>';
                    }}
                }} else {{
                    // Если бесплатная доставка выключена в админке
                    fdWidget.style.display = 'none';
                    if(deliveryCostEl) deliveryCostEl.innerText = finalDelivery.toFixed(2) + ' грн';
                }}
                
                if (count === 0) {{
                    finalDelivery = 0; 
                    fdWidget.style.display = 'none'; // Скрываем виджет, если корзина пуста
                }}
                
                cartTotalEl.textContent = (total + finalDelivery).toFixed(2) + ' грн';
                cartCountEl.textContent = count;
                cartCountEl.style.display = count > 0 ? 'flex' : 'none';
                checkoutBtn.disabled = count === 0;
            }}

            window.updateQty = (key, delta) => {{
                if (cart[key]) {{
                    cart[key].quantity += delta;
                    if (cart[key].quantity <= 0) delete cart[key];
                    saveCart();
                    updateCartView();
                }}
            }};

            function saveCart() {{ localStorage.setItem('webCart', JSON.stringify(cart)); }}

            // Checkout
            const checkoutModal = document.getElementById('checkout-modal');
            const addressGroup = document.getElementById('address-group');
            const timeGroup = document.getElementById('specific-time-group');
            
            checkoutBtn.onclick = () => {{
                cartSidebar.classList.remove('open');
                checkoutModal.classList.add('visible');
                updateCheckoutTotal(); // Recalculate initially

                // --- GA EVENT: begin_checkout ---
                const itemsGA = Object.values(cart).map(i => ({{
                    item_id: i.id.toString(),
                    item_name: i.name,
                    price: i.price,
                    quantity: i.quantity,
                    item_variant: (i.modifiers||[]).map(m=>m.name).join(', ')
                }}));
                const val = itemsGA.reduce((s, i) => s + i.price*i.quantity, 0);
                
                sendGA('begin_checkout', {{
                    currency: 'UAH',
                    value: val,
                    items: itemsGA
                }});
                // --------------------------------
            }};
            
            // --- NEW: Checkout Calculation Logic ---
            function updateCheckoutTotal() {{
                const items = Object.values(cart);
                let subtotal = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
                
                const dType = document.querySelector('input[name="delivery_type"]:checked').value;
                let deliveryPrice = 0;
                
                if (dType === 'delivery') {{
                    if (FREE_DELIVERY_FROM !== null && subtotal >= FREE_DELIVERY_FROM) {{
                        deliveryPrice = 0;
                    }} else {{
                        deliveryPrice = DELIVERY_COST;
                    }}
                }} else {{
                    deliveryPrice = 0; // Pickup
                }}
                
                document.getElementById('checkout-subtotal').innerText = subtotal.toFixed(2) + ' грн';
                
                const delEl = document.getElementById('checkout-delivery');
                if (deliveryPrice === 0) {{
                    delEl.innerHTML = '<span style="color:#22c55e">Безкоштовно</span>';
                }} else {{
                    delEl.innerText = deliveryPrice.toFixed(2) + ' грн';
                }}
                
                document.getElementById('checkout-total').innerText = (subtotal + deliveryPrice).toFixed(2) + ' грн';
            }}
            
            document.querySelectorAll('input[name="delivery_type"]').forEach(el => {{
                el.onchange = (e) => {{
                    const isDelivery = e.target.value === 'delivery';
                    addressGroup.style.display = isDelivery ? 'block' : 'none';
                    document.getElementById('address').required = isDelivery;
                    updateCheckoutTotal(); // Recalculate on change
                }};
            }});
            
            document.querySelectorAll('input[name="delivery_time"]').forEach(el => {{
                el.onchange = (e) => {{
                    timeGroup.style.display = e.target.value === 'specific' ? 'block' : 'none';
                }};
            }});
            
            // --- PHONE VALIDATION & FORMATTING ---
            const phoneInput = document.getElementById('phone_number');
            phoneInput.addEventListener('input', (e) => {{
                let val = e.target.value.replace(/\D/g, ''); // leave digits
                // ensure 380 prefix
                if (!val.startsWith('380')) {{
                    val = '380' + val.replace(/^380/, '');
                }}
                if (val.length > 12) val = val.slice(0, 12);
                e.target.value = '+' + val;
            }});
            
            phoneInput.addEventListener('focus', () => {{
                if(!phoneInput.value) phoneInput.value = '+380';
            }});

            // --- ADDRESS AUTOCOMPLETE (OSM) ---
            const addrInput = document.getElementById('address');
            const suggBox = document.getElementById('address-suggestions');
            let timeoutId;

            addrInput.addEventListener('input', (e) => {{
                const q = e.target.value;
                if (q.length < 3) {{ suggBox.style.display = 'none'; return; }}
                
                clearTimeout(timeoutId);
                timeoutId = setTimeout(async () => {{
                    // Search Ukraine-wide
                    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${{encodeURIComponent(q)}}&countrycodes=ua&limit=5&addressdetails=1&accept-language=uk`;
                    try {{
                        const res = await fetch(url);
                        const data = await res.json();
                        suggBox.innerHTML = '';
                        if (data.length) {{
                            data.forEach(item => {{
                                const div = document.createElement('div');
                                div.className = 'suggestion-item';
                                div.innerHTML = `<i class="fa-solid fa-location-dot"></i> `;
                                
                                // Brief address construction
                                const addr = item.address;
                                const road = addr.road || addr.street || addr.pedestrian || '';
                                const number = addr.house_number || '';
                                const city = addr.city || addr.town || addr.village || '';
                                
                                let label = '';
                                if(road) label += road;
                                if(number) label += (label ? ', ' : '') + number;
                                if(city) label += (label ? ', ' : '') + city;
                                
                                if(!label) label = item.display_name.split(',').slice(0,3).join(',');

                                const span = document.createElement('span');
                                span.innerText = label;
                                div.appendChild(span);
                                
                                div.onclick = () => {{
                                    addrInput.value = label;
                                    suggBox.style.display = 'none';
                                }};
                                suggBox.appendChild(div);
                            }});
                            suggBox.style.display = 'block';
                        }} else {{
                            suggBox.style.display = 'none';
                        }}
                    }} catch(e) {{}}
                }}, 400); // Debounce
            }});
            
            document.addEventListener('click', (e) => {{
                if (!addrInput.contains(e.target) && !suggBox.contains(e.target)) {{
                    suggBox.style.display = 'none';
                }}
            }});

            document.getElementById('phone_number').onblur = async (e) => {{
                if(e.target.value.length >= 13) {{
                    try {{
                        const res = await fetch('/api/customer_info/' + encodeURIComponent(e.target.value));
                        if(res.ok) {{
                            const data = await res.json();
                            if(data.customer_name) document.getElementById('customer_name').value = data.customer_name;
                            if(data.address) document.getElementById('address').value = data.address;
                        }}
                    }} catch(err) {{}}
                }}
            }};

            document.getElementById('checkout-form').onsubmit = async (e) => {{
                e.preventDefault();
                
                // --- PHONE VALIDATION CHECK ---
                if (phoneInput.value.length < 13) {{
                    alert("Будь ласка, введіть коректний номер телефону (+380...)");
                    phoneInput.focus();
                    return;
                }}

                const btn = document.getElementById('place-order-submit');
                const originalText = btn.innerText;
                btn.disabled = true; 
                btn.innerHTML = '<div class="spinner" style="border-color:white; border-top-color:transparent;"></div>';
                
                const dType = document.querySelector('input[name="delivery_type"]:checked').value;
                const tType = document.querySelector('input[name="delivery_time"]:checked').value;
                const payMethod = document.querySelector('input[name="payment_method"]:checked').value;
                let timeVal = "Якнайшвидше";
                if(tType === 'specific') timeVal = document.getElementById('specific_time_input').value || "Не вказано";

                const data = {{
                    customer_name: document.getElementById('customer_name').value,
                    phone_number: document.getElementById('phone_number').value,
                    is_delivery: dType === 'delivery',
                    address: dType === 'delivery' ? document.getElementById('address').value : null,
                    delivery_time: timeVal,
                    payment_method: payMethod,
                    
                    // --- ДОДАВАННЯ КОМЕНТАРЯ В JS ---
                    comment: document.getElementById('order_comment').value,
                    // ---------------------------------
                    
                    items: Object.values(cart)
                }};

                try {{
                    const res = await fetch('/api/place_order', {{
                        method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data)
                    }});
                    if(res.ok) {{
                        // --- GA EVENT: purchase (Analytics) ---
                        const itemsGA = Object.values(cart).map(i => ({{
                            item_id: i.id.toString(),
                            item_name: i.name,
                            price: i.price,
                            quantity: i.quantity
                        }}));
                        const val = itemsGA.reduce((s, i) => s + i.price*i.quantity, 0);
                        
                        sendGA('purchase', {{
                            transaction_id: 'order_' + Date.now(), 
                            currency: 'UAH',
                            value: val,
                            items: itemsGA
                        }});
                        
                        // --- GOOGLE ADS: CONVERSION (DIRECT) ---
                        // Відправка конверсії безпосередньо в Ads (мимо Analytics)
                        sendAdsConversion(val, 'order_' + Date.now());
                        // ---------------------------------------

                        cart = {{}}; saveCart(); updateCartView();
                        checkoutModal.classList.remove('visible');
                        
                        // Show Beautiful Success Modal
                        document.getElementById('success-modal').classList.add('visible');
                        
                    }} else {{ alert('Помилка. Спробуйте ще раз.'); }}
                }} catch(err) {{ alert('Помилка з`єднання'); }} 
                finally {{ btn.disabled = false; btn.innerText = originalText; }}
            }};

            // Utils
            document.getElementById('cart-toggle').onclick = () => cartSidebar.classList.add('open');
            document.getElementById('close-cart-btn').onclick = () => cartSidebar.classList.remove('open');
            
            // New Listener
            document.getElementById('open-zones-btn').onclick = () => document.getElementById('zones-modal').classList.add('visible');

            document.querySelectorAll('.close-modal').forEach(btn => {{
                btn.onclick = (e) => {{
                    e.target.closest('.modal-overlay').classList.remove('visible');
                    // Reset URL if product modal closed
                    if(e.target.closest('#product-modal')) {{
                         window.history.pushState({{}}, '', window.location.pathname);
                         // НОВЕ: Повертаємо заголовок
                         if (typeof SEO_TEMPLATES !== 'undefined') {{
                             document.title = SEO_TEMPLATES.site_title;
                         }}
                    }}
                }};
            }});

            // Page Modal Logic
            const pageModal = document.getElementById('page-modal');
            document.body.addEventListener('click', async (e) => {{
                const link = e.target.closest('.menu-popup-trigger');
                if (link) {{
                    e.preventDefault();
                    pageModal.classList.add('visible');
                    document.getElementById('page-modal-body').innerHTML = '<div style="text-align:center; padding:60px;"><div class="spinner"></div></div>';
                    document.getElementById('page-modal-title').innerText = link.innerText;
                    try {{
                        const res = await fetch('/api/page/' + link.dataset.itemId);
                        if(res.ok) {{
                            const d = await res.json();
                            document.getElementById('page-modal-title').innerText = d.title;
                            document.getElementById('page-modal-body').innerHTML = d.content;
                        }} else {{
                            throw new Error("Not found");
                        }}
                    }} catch(err) {{ 
                        document.getElementById('page-modal-body').innerText = 'Не вдалося завантажити сторінку.'; 
                    }}
                }}
            }});

            function setupScrollSpy() {{
                const observer = new IntersectionObserver(entries => {{
                    entries.forEach(entry => {{
                        if (entry.isIntersecting) {{
                            document.querySelectorAll('.category-nav a').forEach(l => l.classList.remove('active'));
                            const active = document.querySelector(`.category-nav a[href="#${{entry.target.id}}"]`);
                            if(active) {{
                                active.classList.add('active');
                                active.scrollIntoView({{behavior:'smooth', inline:'center', block: 'nearest'}});
                            }}
                        }}
                    }});
                }}, {{rootMargin: '-20% 0px -70% 0px'}});
                document.querySelectorAll('.category-section').forEach(s => observer.observe(s));
            }}
        }});
    </script>
</body>
</html>
"""