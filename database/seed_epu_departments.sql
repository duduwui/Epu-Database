-- Seed all 13 EPU colleges & institutes
-- Source: official EPU admission table (Sorani Kurdish)

INSERT INTO departments (name, code, description) VALUES
  ('کۆلێژی تەندروستی — College of Health Sciences',       'CHS', 'شیکاری نەخۆشی، تیشک، چارەسەری سروشتی'),
  ('کۆلێژی ئەندازیاری — College of Engineering',           'COE', 'شارستانی، رێگوبان، میکانیک و وزە'),
  ('کۆلێژی ئەندازیاری کۆمپیوتەر — College of Computer Engineering', 'CCE', 'زیرەکی دەستکرد، سیستەمی زانیاری، تەکنەلۆجیای زانیاری و گەیاندن'),
  ('کۆلێژی تەکنەلۆجی — College of Technology',             'COT', 'کەرەستە، نۆتڕۆمیتل، پشەسازی، نەوت، رێگوبان، رووپینوان، کانزاکان'),
  ('کۆلێژی کارگێڕی — College of Administration',           'COA', 'کارگێڕی کار، میدیا، بازاڕگەڕی، ئامێڕباری'),
  ('پەیمانگای پزیشکی — Medical Institute',                 'PMI', 'دەرمانسازی، پەرستاری، شیکاری نەخۆشی، سرکردن، یاریدەدەری ددان'),
  ('پەیمانگای کارگێڕی — Administrative Institute',         'MIS', 'کارگێڕی کار، یاسا، بازاڕگەڕی، گەشتیاری، MIS، سەرچاوە مرۆییەکان، میدیا، کتێبخانە، ئامێڕباری'),
  ('کۆلێژی تەکنیکی شەقلاوە — Shaqlawa Technical College',  'STC', 'شیکاری، فتنەمی، پەرستاری، IT، کارگێڕی، MIS، گەشتیاری، تەلارسازی، دیپلۆماسی، بیناکاری، خۆراک'),
  ('پەیمانگای تەکنیکی کۆیە — Koya Technical Institute',    'KTI', 'پەرستاری، شیکاری، لەدایکبوون، IT، کارگێڕی، گەشتیاری، نەوت'),
  ('پەیمانگای تەکنیکی سۆران — Soran Technical Institute',  'STI', 'پەرستاری، شیکاری، لەدایکبوون، کارگێڕی، IT، ئامێڕباری'),
  ('پەیمانگای تەکنیکی مێرگەسوور — Mergasur Technical Institute', 'MTI', 'کارگێڕی، پەرستاری، بەخێوکردنی هەنگ، پزیشکی ئاژەڵ'),
  ('پەیمانگای تەکنیکی چۆمان — Choman Technical Institute', 'CTI', 'IT، کارگێڕی، تەلارسازی، کارگێڕی دارایی'),
  ('پەیمانگای تەکنیکی خەبات — Khabat Technical Institute', 'KHI', 'تەندروستی گشتی، IT، یاسا، پزیشکی ئاژەڵ، پاراستنی رووەک، ئاسایشی خۆراک')
ON CONFLICT (code) DO NOTHING;
