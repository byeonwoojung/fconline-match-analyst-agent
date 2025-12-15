/**
 * FC Online 서버 점검 공지 크롤러
 * 
 * Puppeteer를 사용하여 https://fconline.nexon.com/news/notice/list 에서
 * '점검' 카테고리의 공지사항을 수집합니다.
 * 
 * 특징:
 * - 2달 전까지의 점검 공지 수집
 * - 중단/재시작 가능 (visited.json으로 방문 기록 관리)
 * - 게시글마다 실시간 JSONL append
 * - 이미지는 "[img 자리]"로 표시
 * - 페이지 방문 후 '점검' 필터 재클릭 필요
 */

import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// ES Module에서 __dirname 대체
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ============================================================================
// 설정 상수
// ============================================================================
const CONFIG = {
  BASE_URL: 'https://fconline.nexon.com/news/notice/list',
  // Rate limiting (밀리초)
  DELAY: {
    BETWEEN_POSTS_MIN: 2000,     // 게시글 간 최소 2초
    BETWEEN_POSTS_MAX: 4000,     // 게시글 간 최대 4초
    EVERY_10_POSTS_MIN: 10000,   // 10개 게시글마다 최소 10초
    EVERY_10_POSTS_MAX: 15000,   // 10개 게시글마다 최대 15초
    BETWEEN_PAGES_MIN: 2000,     // 페이지 간 최소 2초
    BETWEEN_PAGES_MAX: 4000,     // 페이지 간 최대 4초
    EVERY_3_PAGES_MIN: 60000,    // 3페이지마다 최소 1분
    EVERY_3_PAGES_MAX: 180000,   // 3페이지마다 최대 3분
    EVERY_10_PAGES_MIN: 480000,  // 10페이지마다 최소 8분
    EVERY_10_PAGES_MAX: 720000,  // 10페이지마다 최대 12분
  },
  // 타임아웃 설정
  TIMEOUT: {
    PAGE_LOAD: 180000,          // 페이지 로딩 타임아웃 3분
    RECOVERY_WAIT: 900000,      // 타임아웃 후 복구 대기 15분
  },
  // 2달 전까지 수집
  MONTHS_TO_CRAWL: 2,
};

// ============================================================================
// 유틸리티 함수
// ============================================================================

/**
 * 랜덤 딜레이 (min~max 밀리초)
 */
function randomDelay(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * sleep 함수
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 한국 시간 (KST) 기준 현재 날짜 정보 반환
 */
function getKSTDate() {
  const now = new Date();
  // UTC+9
  const kstOffset = 9 * 60 * 60 * 1000;
  const kstDate = new Date(now.getTime() + kstOffset);
  return kstDate;
}

/**
 * Date 객체를 YY-MM-DD 형식 문자열로 변환
 */
function formatDateToYYMMDD(date) {
  const year = String(date.getUTCFullYear()).slice(-2);
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 게시판 날짜 문자열을 Date 객체로 파싱
 * 형식: "2025.12.09" 또는 "5일 전", "11.25(화)" 등
 */
function parseNoticeDate(dateStr) {
  const kst = getKSTDate();
  
  // "5일 전" 형식
  if (dateStr.includes('일 전')) {
    const daysAgo = parseInt(dateStr.match(/(\d+)일 전/)[1]);
    kst.setUTCDate(kst.getUTCDate() - daysAgo);
    return kst;
  }
  
  // "11.25(화)" 또는 "11.25" 형식
  const shortMatch = dateStr.match(/(\d+)\.(\d+)/);
  if (shortMatch && !dateStr.includes('.') || (shortMatch && dateStr.split('.').length === 2)) {
    const month = parseInt(shortMatch[1]);
    const day = parseInt(shortMatch[2]);
    // 현재 연도 또는 작년으로 추정
    let year = kst.getUTCFullYear();
    // 만약 현재 월보다 미래의 월이면 작년으로 간주
    if (month > kst.getUTCMonth() + 1) {
      year -= 1;
    }
    return new Date(Date.UTC(year, month - 1, day));
  }
  
  // "2025.12.09" 형식 (상세 페이지)
  const fullMatch = dateStr.match(/(\d{4})\.(\d{2})\.(\d{2})/);
  if (fullMatch) {
    const [, year, month, day] = fullMatch.map(Number);
    return new Date(Date.UTC(year, month - 1, day));
  }
  
  return null;
}

/**
 * N달 전 날짜 계산
 */
function getDateMonthsAgo(months) {
  const kst = getKSTDate();
  kst.setUTCMonth(kst.getUTCMonth() - months);
  return kst;
}

/**
 * 오늘 날짜 폴더 경로 반환
 */
function getTodayDataDir() {
  const kst = getKSTDate();
  const dateStr = formatDateToYYMMDD(kst);
  return path.join(__dirname, '..', 'data', dateStr);
}

// ============================================================================
// 방문 기록 관리
// ============================================================================

/**
 * data/ 폴더 경로 반환 (날짜 폴더가 아닌 상위 폴더)
 */
function getDataRootDir() {
  return path.join(__dirname, '..', 'data');
}

class VisitedManager {
  constructor() {
    // data/ 폴더에 직접 visited.json 저장 (날짜 폴더가 아닌 공용)
    const dataRootDir = getDataRootDir();
    if (!fs.existsSync(dataRootDir)) {
      fs.mkdirSync(dataRootDir, { recursive: true });
    }
    this.filePath = path.join(dataRootDir, 'visited.json');
    this.visited = new Set();
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.filePath)) {
        const data = JSON.parse(fs.readFileSync(this.filePath, 'utf-8'));
        this.visited = new Set(data.visited || []);
        console.log(`📋 기존 방문 기록 로드: ${this.visited.size}개 게시글`);
      }
    } catch (e) {
      console.log('📋 새로운 방문 기록 시작');
      this.visited = new Set();
    }
  }

  save() {
    const data = { visited: Array.from(this.visited) };
    fs.writeFileSync(this.filePath, JSON.stringify(data, null, 2), 'utf-8');
  }

  has(articleNo) {
    return this.visited.has(articleNo);
  }

  add(articleNo) {
    this.visited.add(articleNo);
    this.save();
  }

  get count() {
    return this.visited.size;
  }
}

// ============================================================================
// JSONL Writer
// ============================================================================

class JsonlWriter {
  constructor(dataDir) {
    this.filePath = path.join(dataDir, 'maintenance.jsonl');
    // 파일이 없으면 빈 파일 생성
    if (!fs.existsSync(this.filePath)) {
      fs.writeFileSync(this.filePath, '', 'utf-8');
      console.log(`📝 새 JSONL 파일 생성: ${this.filePath}`);
    }
  }

  append(data) {
    const line = JSON.stringify(data, null, 0) + '\n';
    fs.appendFileSync(this.filePath, line, 'utf-8');
  }
}

// ============================================================================
// HTML 파싱 함수
// ============================================================================

/**
 * HTML에서 텍스트 추출 (이미지는 [img 자리]로 대체)
 */
function parseContentBody(html) {
  if (!html) return '';
  
  // <img> 태그를 [img 자리]로 대체
  let text = html.replace(/<img[^>]*>/gi, '[img 자리]');
  
  // <br>, </p>, </div> 등을 줄바꿈으로 변환
  text = text.replace(/<br\s*\/?>/gi, '\n');
  text = text.replace(/<\/p>/gi, '\n');
  text = text.replace(/<\/div>/gi, '\n');
  text = text.replace(/<\/li>/gi, '\n');
  
  // 나머지 HTML 태그 제거
  text = text.replace(/<[^>]+>/g, '');
  
  // HTML 엔티티 디코딩
  text = text.replace(/&nbsp;/g, ' ');
  text = text.replace(/&lt;/g, '<');
  text = text.replace(/&gt;/g, '>');
  text = text.replace(/&amp;/g, '&');
  text = text.replace(/&quot;/g, '"');
  text = text.replace(/&#39;/g, "'");
  
  // 연속된 공백/줄바꿈 정리
  text = text.replace(/[ \t]+/g, ' ');
  text = text.replace(/\n\s*\n/g, '\n\n');
  text = text.trim();
  
  return text;
}

// ============================================================================
// 메인 크롤러
// ============================================================================

async function crawl() {
  console.log('🚀 FC Online 서버 점검 공지 크롤러 시작');
  console.log(`📅 수집 기간: 최근 ${CONFIG.MONTHS_TO_CRAWL}개월`);
  
  // 데이터 디렉토리 설정
  const dataDir = getTodayDataDir();
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
    console.log(`📁 데이터 디렉토리 생성: ${dataDir}`);
  }
  
  // 방문 기록 및 JSONL 작성자 초기화
  const visited = new VisitedManager();
  const writer = new JsonlWriter(dataDir);
  
  // 수집 기한 (2달 전)
  const cutoffDate = getDateMonthsAgo(CONFIG.MONTHS_TO_CRAWL);
  console.log(`📆 수집 기한: ${cutoffDate.toISOString().split('T')[0]} 이후 게시글만 수집`);
  
  // 브라우저 시작
  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--window-size=1920,1080'
    ]
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
  
  let totalCrawled = 0;
  
  try {
    // 목록 페이지로 이동
    console.log(`🌐 공지사항 페이지로 이동: ${CONFIG.BASE_URL}`);
    await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle2', timeout: 60000 });
    await sleep(randomDelay(2000, 3000));
    
    // '점검' 필터 클릭
    await clickMaintenanceFilter(page);
    await sleep(randomDelay(2000, 3000));
    
    let pageNum = 1;
    let shouldStop = false;
    
    while (!shouldStop) {
      console.log(`\n📄 페이지 ${pageNum} 크롤링 중...`);
      
      // 현재 페이지의 게시글 목록 가져오기
      const articles = await page.evaluate(() => {
        const items = [];
        const rows = document.querySelectorAll('.list_wrap .tbody .tr');
        
        for (const row of rows) {
          const dataNo = row.getAttribute('data-no');
          const link = row.querySelector('a');
          const dateSpan = row.querySelector('.td.date');
          const titleSpan = row.querySelector('.td.subject');
          const viewsSpan = row.querySelector('.td.count');
          
          if (dataNo && link) {
            items.push({
              article_no: parseInt(dataNo),
              href: link.getAttribute('href'),
              title: titleSpan ? titleSpan.textContent.trim() : '',
              date_str: dateSpan ? dateSpan.textContent.trim() : '',
              views: viewsSpan ? viewsSpan.textContent.trim().replace(/,/g, '') : '0'
            });
          }
        }
        
        return items;
      });
      
      console.log(`📋 ${articles.length}개 게시글 발견`);
      
      if (articles.length === 0) {
        console.log('⚠️ 게시글이 없습니다. 크롤링 종료.');
        break;
      }
      
      let crawledInThisPage = 0;
      let visitedDetailPage = false;
      
      for (let i = 0; i < articles.length; i++) {
        const article = articles[i];
        
        // 이미 방문한 게시글 스킵
        if (visited.has(article.article_no)) {
          console.log(`⏭️ [${article.article_no}] 이미 방문함 - 스킵`);
          continue;
        }
        
        // 날짜 체크 (2달 전보다 오래된 게시글이면 중단)
        const articleDate = parseNoticeDate(article.date_str);
        if (articleDate && articleDate < cutoffDate) {
          console.log(`📅 [${article.article_no}] ${article.date_str} - 수집 기한(${CONFIG.MONTHS_TO_CRAWL}개월) 초과, 크롤링 종료`);
          shouldStop = true;
          break;
        }
        
        // 상세 페이지 방문
        console.log(`\n🔍 [${article.article_no}] "${article.title}" 방문 중...`);
        
        try {
          // 상세 페이지로 이동 (타임아웃 3분)
          const articleUrl = `https://fconline.nexon.com${article.href}`;
          
          try {
            await page.goto(articleUrl, { waitUntil: 'networkidle2', timeout: CONFIG.TIMEOUT.PAGE_LOAD });
          } catch (gotoErr) {
            console.log(`⚠️ 페이지 로드 타임아웃 (3분 초과). 15분 대기 후 재시도...`);
            
            // 메인 페이지로 이동
            try {
              await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle2', timeout: 60000 });
            } catch (e) {
              await page.reload({ waitUntil: 'networkidle2', timeout: 60000 });
            }
            
            // 15분 대기
            await sleep(CONFIG.TIMEOUT.RECOVERY_WAIT);
            
            // 재시도
            try {
              await page.goto(articleUrl, { waitUntil: 'networkidle2', timeout: CONFIG.TIMEOUT.PAGE_LOAD });
            } catch (retryErr) {
              throw new Error(`❌ 게시글 ${article.article_no} 로드 최종 실패`);
            }
          }
          
          visitedDetailPage = true;
          await sleep(randomDelay(1500, 2500));
          
          // 상세 페이지에서 정보 추출
          const detail = await page.evaluate(() => {
            const result = {
              category: '',
              title: '',
              author: '',
              date: '',
              views: '',
              content_html: '',
            };
            
            // 카테고리 (점검)
            const categoryEl = document.querySelector('.view_header .th.sort');
            if (categoryEl) result.category = categoryEl.textContent.trim();
            
            // 제목
            const titleEl = document.querySelector('.view_header .th.subject');
            if (titleEl) result.title = titleEl.textContent.trim();
            
            // 작성자
            const authorEl = document.querySelector('.view_header .th.author');
            if (authorEl) result.author = authorEl.textContent.trim();
            
            // 날짜
            const dateEl = document.querySelector('.view_header .th.date');
            if (dateEl) result.date = dateEl.textContent.trim();
            
            // 조회수
            const viewsEl = document.querySelector('.view_header .th.count');
            if (viewsEl) result.views = viewsEl.textContent.trim().replace(/,/g, '');
            
            // 본문 HTML
            const contentEl = document.querySelector('.content_body');
            if (contentEl) result.content_html = contentEl.innerHTML;
            
            return result;
          });
          
          // 본문 텍스트 추출 (이미지는 [img 자리]로)
          const contentText = parseContentBody(detail.content_html);
          
          // 데이터 구성
          const postData = {
            article_no: article.article_no,
            category: detail.category,
            title: detail.title,
            author: detail.author,
            date: detail.date,
            views: parseInt(detail.views) || 0,
            content: contentText,
            url: articleUrl,
            crawled_at: new Date().toISOString(),
          };
          
          // JSONL에 저장
          writer.append(postData);
          visited.add(article.article_no);
          totalCrawled++;
          crawledInThisPage++;
          
          console.log(`✅ [${article.article_no}] 저장 완료 (총 ${totalCrawled}개)`);
          
          // 게시글 간 딜레이
          await sleep(randomDelay(CONFIG.DELAY.BETWEEN_POSTS_MIN, CONFIG.DELAY.BETWEEN_POSTS_MAX));
          
          // 10개 게시글마다 추가 휴식
          if (totalCrawled % 10 === 0) {
            const extraDelay = randomDelay(CONFIG.DELAY.EVERY_10_POSTS_MIN, CONFIG.DELAY.EVERY_10_POSTS_MAX);
            console.log(`⏸️ ${totalCrawled}개 수집 완료, ${Math.round(extraDelay / 1000)}초 휴식...`);
            await sleep(extraDelay);
          }
          
        } catch (err) {
          console.error(`❌ [${article.article_no}] 크롤링 실패:`, err.message);
          // 에러가 발생하면 throw하여 크롤링 중단 (finally에서 저장됨)
          if (err.message.includes('최종 실패')) {
            throw err;
          }
        }
      }
      
      // 페이지 완료 후 휴식
      if (crawledInThisPage > 0) {
        // 10페이지마다 휴식 (8~12분)
        if (pageNum % 10 === 0) {
          const longDelay = randomDelay(CONFIG.DELAY.EVERY_10_PAGES_MIN, CONFIG.DELAY.EVERY_10_PAGES_MAX);
          console.log(`\n☕ ${pageNum}페이지 완료 (${crawledInThisPage}개 수집). ${Math.round(longDelay / 60000)}분 휴식...`);
          await sleep(longDelay);
        }
        // 3페이지마다 휴식 (1~3분)
        else if (pageNum % 3 === 0) {
          const shortDelay = randomDelay(CONFIG.DELAY.EVERY_3_PAGES_MIN, CONFIG.DELAY.EVERY_3_PAGES_MAX);
          console.log(`\n⏸️ ${pageNum}페이지 완료 (${crawledInThisPage}개 수집). ${Math.round(shortDelay / 60000)}분 휴식...`);
          await sleep(shortDelay);
        }
      } else {
        console.log(`📄 페이지 ${pageNum}: 새로 수집한 게시글 없음, 휴식 없이 계속 진행`);
      }
      
      if (shouldStop) break;
      
      // 목록 페이지로 돌아가기 (상세 페이지를 방문했으면)
      if (visitedDetailPage) {
        console.log(`🔙 목록 페이지로 돌아가기...`);
        await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle2', timeout: 60000 });
        await sleep(randomDelay(1500, 2500));
        
        // '점검' 필터 다시 클릭
        await clickMaintenanceFilter(page);
        await sleep(randomDelay(1500, 2500));
      }
      
      // 다음 페이지로 이동
      pageNum++;
      
      try {
        console.log(`🔄 페이지 ${pageNum}로 이동 중...`);
        
        // Article.ArticleList 함수로 직접 페이지 이동 (점검 카테고리: n4ArticleCategorySN=2)
        const navigated = await page.evaluate((targetPage) => {
          if (typeof Article !== 'undefined' && Article.ArticleList) {
            Article.ArticleList(null, targetPage, '#divListPart', '', 'Title', '2', '0', '/news/notice');
            return true;
          }
          return false;
        }, pageNum);
        
        if (!navigated) {
          console.log('⚠️ Article.ArticleList 함수를 찾을 수 없습니다.');
          break;
        }
        
        // 페이지 로드 대기 함수
        const waitForPageLoad = async (targetPage) => {
          const pageLoadStart = Date.now();
          
          while (Date.now() - pageLoadStart < CONFIG.TIMEOUT.PAGE_LOAD) {
            await sleep(2000);
            
            const currentPageCheck = await page.evaluate(() => {
              const active = document.querySelector('.pagination_wrap li.active span');
              return active ? parseInt(active.textContent) : null;
            });
            
            if (currentPageCheck === targetPage) {
              return true;
            }
            
            // 30초마다 로딩 상태 로그
            if ((Date.now() - pageLoadStart) % 30000 < 2000) {
              console.log(`⏳ 페이지 ${targetPage} 로딩 대기 중... (${Math.round((Date.now() - pageLoadStart) / 1000)}초 경과)`);
            }
          }
          return false;
        };
        
        // 첫 번째 시도
        let pageLoaded = await waitForPageLoad(pageNum);
        
        if (!pageLoaded) {
          console.log(`⚠️ 페이지 ${pageNum} 로드 타임아웃 (3분 초과). 15분 대기 후 재시도...`);
          
          // 메인 페이지로 이동
          try {
            await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle2', timeout: 60000 });
          } catch (gotoErr) {
            await page.reload({ waitUntil: 'networkidle2', timeout: 60000 });
          }
          
          // '점검' 필터 다시 클릭
          await clickMaintenanceFilter(page);
          
          // 15분 대기
          console.log(`🔄 메인 페이지로 이동 완료. ${Math.round(CONFIG.TIMEOUT.RECOVERY_WAIT / 60000)}분 대기 중...`);
          await sleep(CONFIG.TIMEOUT.RECOVERY_WAIT);
          console.log(`🔄 대기 완료, 페이지 ${pageNum}로 재이동 시도...`);
          
          // 다시 페이지 이동 시도
          await page.evaluate((targetPage) => {
            if (typeof Article !== 'undefined' && Article.ArticleList) {
              Article.ArticleList(null, targetPage, '#divListPart', '', 'Title', '2', '0', '/news/notice');
            }
          }, pageNum);
          
          // 두 번째 시도
          pageLoaded = await waitForPageLoad(pageNum);
          
          if (!pageLoaded) {
            throw new Error(`❌ 페이지 ${pageNum} 이동 최종 실패 (재시도 후에도 응답 없음). 크롤링 중단.`);
          }
        }
        
        console.log(`📄 페이지 ${pageNum}로 이동 완료`);
        
      } catch (e) {
        console.log('⚠️ 페이지 이동 실패:', e.message);
        throw e;
      }
      
      // 페이지 간 딜레이
      const pageDelay = randomDelay(CONFIG.DELAY.BETWEEN_PAGES_MIN, CONFIG.DELAY.BETWEEN_PAGES_MAX);
      await sleep(pageDelay);
    }
    
  } catch (e) {
    console.error('❌ 크롤링 중 오류 발생:', e);
  } finally {
    await browser.close();
    console.log(`\n🎉 크롤링 완료! 총 ${totalCrawled}개 점검 공지 수집됨.`);
    console.log(`📁 저장 위치: ${dataDir}`);
    
    // JSONL 파일을 article_no 내림차순으로 재정렬
    const jsonlPath = path.join(dataDir, 'maintenance.jsonl');
    if (fs.existsSync(jsonlPath)) {
      console.log('\n📊 게시글 정렬 중 (article_no 내림차순)...');
      try {
        const content = fs.readFileSync(jsonlPath, 'utf-8');
        const lines = content.split('\n').filter(line => line.trim());
        const posts = lines.map(line => JSON.parse(line));
        
        // article_no 내림차순 정렬
        posts.sort((a, b) => b.article_no - a.article_no);
        
        // 다시 JSONL로 저장
        const sortedContent = posts.map(post => JSON.stringify(post)).join('\n') + '\n';
        fs.writeFileSync(jsonlPath, sortedContent);
        console.log(`✅ ${posts.length}개 게시글 정렬 완료`);
      } catch (sortErr) {
        console.error('⚠️ 정렬 중 오류:', sortErr.message);
      }
    }
  }
}

/**
 * '점검' 필터 클릭
 */
async function clickMaintenanceFilter(page) {
  console.log(`🔧 '점검' 필터 클릭...`);
  
  try {
    // radioSort03 (점검) 라벨 클릭
    await page.evaluate(() => {
      const label = document.querySelector('label[for="radioSort03"]');
      if (label) {
        label.click();
        return true;
      }
      return false;
    });
    
    // 필터 적용 대기
    await sleep(randomDelay(1500, 2500));
    
    // 필터가 적용되었는지 확인
    const isChecked = await page.evaluate(() => {
      const radio = document.getElementById('radioSort03');
      return radio ? radio.checked : false;
    });
    
    if (isChecked) {
      console.log(`✅ '점검' 필터 적용됨`);
    } else {
      console.log(`⚠️ '점검' 필터 적용 확인 실패, 재시도...`);
      await page.click('label[for="radioSort03"]');
      await sleep(randomDelay(1000, 2000));
    }
  } catch (err) {
    console.error(`❌ '점검' 필터 클릭 실패:`, err.message);
  }
}

// 실행
crawl().catch(console.error);
