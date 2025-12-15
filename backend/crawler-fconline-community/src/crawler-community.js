/**
 * FC Online 커뮤니티 자유게시판 크롤러
 * 
 * Puppeteer를 사용하여 https://fconline.nexon.com/community/free 게시판을
 * 1달 전까지의 게시글을 수집합니다.
 * 
 * 특징:
 * - 중단/재시작 가능 (visited.json으로 방문 기록 관리)
 * - 게시글마다 실시간 JSONL append
 * - 스쿼드 메이커 정보 파싱 지원
 * - Rate limiting (게시글 간 0.5~2초, 페이지 간 1~3초, 10페이지마다 10~15초, 30페이지마다 1분~1분20초)
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
  BASE_URL: 'https://fconline.nexon.com/community/free',
  // Rate limiting (밀리초) - GitHub Actions에서 안정적으로 동작하도록 충분한 딜레이
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
  // 1달 전까지 수집
  MONTHS_TO_CRAWL: 1,
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
 * 요일 문자열 반환 (한글)
 */
function getDayOfWeek(date) {
  const days = ['일', '월', '화', '수', '목', '금', '토'];
  return days[date.getUTCDay()];
}

/**
 * 게시판 날짜 문자열을 Date 객체로 파싱
 * data-no 속성: "2025-06-26 16:25:52"
 */
function parseDateFromDataNo(dateStr) {
  // "2025-06-26 16:25:52" -> Date
  const [datePart, timePart] = dateStr.split(' ');
  const [year, month, day] = datePart.split('-').map(Number);
  const [hour, minute, second] = timePart.split(':').map(Number);
  
  // KST로 생성 (UTC+9이므로 UTC로 변환)
  const utcDate = new Date(Date.UTC(year, month - 1, day, hour - 9, minute, second));
  return utcDate;
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
    this.filePath = path.join(dataDir, 'posts.jsonl');
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
// 스쿼드 파서
// ============================================================================

async function parseSquad(page) {
  try {
    const hasSquad = await page.$('.squad');
    if (!hasSquad) return null;

    const squadData = await page.evaluate(() => {
      const squad = document.querySelector('.squad');
      if (!squad) return null;

      // Meta 정보
      const meta = {};
      
      // 총 급여
      const payEl = squad.querySelector('.squad__info-panel__pay .content strong.edit');
      const payCapEl = squad.querySelector('.squad__info-panel__pay .content .txt');
      if (payEl) {
        meta.total_pay = parseInt(payEl.textContent.trim()) || 0;
        if (payCapEl) {
          const match = payCapEl.textContent.match(/\/(\d+)/);
          meta.total_pay_cap = match ? parseInt(match[1]) : 0;
        }
      }

      // 선수 가치
      const priceEl = squad.querySelector('.squad__info-panel__price .content strong');
      if (priceEl) {
        meta.squad_value_bp_text = priceEl.textContent.trim();
        meta.squad_value_bp_raw = priceEl.getAttribute('title') || priceEl.getAttribute('alt') || '';
      }

      // 평균 OVR
      meta.ovr_avg = {};
      const ovrWraps = squad.querySelectorAll('.squad__info-panel__ovr .value_wrap');
      ovrWraps.forEach(wrap => {
        const tit = wrap.querySelector('.tit')?.textContent.trim();
        const value = parseInt(wrap.querySelector('.value')?.textContent.trim()) || 0;
        if (tit) meta.ovr_avg[tit] = value;
      });
      const totalAvr = squad.querySelector('.value_total_avr');
      if (totalAvr) meta.ovr_avg.TOTAL = parseInt(totalAvr.textContent.trim()) || 0;

      // 선수 인원
      const playerCountEl = squad.querySelector('.squad__info-panel__players .content strong');
      if (playerCountEl) {
        meta.player_count = parseInt(playerCountEl.textContent.trim()) || 0;
      }

      // 포메이션 코드
      const fieldEl = squad.querySelector('.squadmaker-view__field');
      if (fieldEl) {
        const classes = fieldEl.className.split(' ');
        const formation = classes.find(c => c.startsWith('f') && /^\d/.test(c.slice(1)));
        meta.formation_code = formation || null;
      }

      // 평균 프로필 (나이, 키, 몸무게)
      const profileEl = squad.querySelector('.total-player__info');
      if (profileEl) {
        const text = profileEl.textContent;
        const ageMatch = text.match(/(\d+)세/);
        const heightMatch = text.match(/(\d+)cm/);
        const weightMatch = text.match(/(\d+)kg/);
        meta.avg_profile = {
          age: ageMatch ? `${ageMatch[1]}세` : null,
          height: heightMatch ? `${heightMatch[1]}cm` : null,
          weight: weightMatch ? `${weightMatch[1]}kg` : null,
        };
      }

      // 팀 컬러
      const teamColors = [];
      const tcButtons = squad.querySelectorAll('.btn_teamcolor');
      tcButtons.forEach(btn => {
        if (btn.classList.contains('disable')) return;
        
        const tcData = {};
        const titEl = btn.querySelector('.teamcolor_tit');
        tcData.type = titEl?.textContent.trim() || '';
        
        const nameEl = btn.querySelector('.teamcolor_item_add_item_tit_txt');
        tcData.name = nameEl?.textContent.trim() || '';
        
        const countEl = btn.querySelector('.teamcolor_item_add_item_tit_num');
        const countMatch = countEl?.textContent.match(/(\d+)/);
        tcData.count = countMatch ? parseInt(countMatch[1]) : 0;
        
        tcData.bonus = [];
        const bonusItems = btn.querySelectorAll('.teamcolor_item_add_item');
        bonusItems.forEach(item => {
          const stat = item.querySelector('.teamcolor_item_add_item_tit')?.textContent.trim();
          const value = item.querySelector('.teamcolor_item_add_item_ab')?.textContent.trim();
          if (stat && value) {
            tcData.bonus.push({ stat, value });
          }
        });
        
        if (tcData.name) teamColors.push(tcData);
      });

      // 선수 정보
      const players = [];
      const playerDivs = squad.querySelectorAll('.squadmaker-view__field > .player');
      playerDivs.forEach(playerDiv => {
        const wrap = playerDiv.querySelector('.player_wrap');
        if (!wrap) return;

        const player = {};
        
        // 포메이션 플레이어 ID
        player.formation_player_id = playerDiv.id || null;
        
        // 슬롯 역할 (gk, rcb, lcb 등)
        const classes = playerDiv.className.split(' ');
        player.slot_role = classes.find(c => !['player', wrap.className.split(' ').find(x => x.startsWith('_'))].includes(c) && c !== '') || null;
        
        // 카드 등급
        const cardClass = Array.from(wrap.classList).find(c => c.startsWith('_'));
        player.card_grade = cardClass ? cardClass.slice(1) : null;
        
        // 선수 이름
        player.name = wrap.getAttribute('title') || '';
        
        // SPID
        const abilityLink = wrap.querySelector('.btn_ability');
        if (abilityLink) {
          const href = abilityLink.getAttribute('href') || '';
          const spidMatch = href.match(/spid=(\d+)/);
          player.spid = spidMatch ? spidMatch[1] : null;
        }
        
        // 포지션
        const posEl = wrap.querySelector('.position');
        player.position_text = posEl?.textContent.trim() || '';
        
        // OVR
        const ovrEl = wrap.querySelector('.ovr');
        player.ovr = parseInt(ovrEl?.textContent.trim()) || 0;
        
        // 급여
        const payEl = wrap.querySelector('.pay span:last-child');
        player.pay = parseInt(payEl?.textContent.trim()) || 0;
        
        // 강화 단계
        const enhanceEl = wrap.querySelector('.en_wrap .ability');
        if (enhanceEl) {
          const enhanceClass = Array.from(enhanceEl.classList).find(c => c.startsWith('en_level'));
          player.enhance_level = enhanceClass ? parseInt(enhanceClass.replace('en_level', '')) : 0;
        }
        
        // 빌드업
        const buildupEl = wrap.querySelector('.buildup');
        if (buildupEl) {
          const buildupClass = Array.from(buildupEl.classList).find(c => c.startsWith('buildup__'));
          player.buildup = buildupClass ? parseInt(buildupClass.replace('buildup__', '')) : 0;
        }
        
        // 가격
        const priceEl = wrap.querySelector('.price');
        if (priceEl) {
          player.price_text = priceEl.textContent.trim();
          player.price_raw = priceEl.getAttribute('title') || priceEl.getAttribute('alt') || '';
        }
        
        // UI 위치
        const style = playerDiv.getAttribute('style') || '';
        const leftMatch = style.match(/left:\s*([\d.]+)%/);
        const topMatch = style.match(/top:\s*([\d.]+)%/);
        const zMatch = style.match(/z-index:\s*(\d+)/);
        player.ui = {
          left_pct: leftMatch ? parseFloat(leftMatch[1]) : null,
          top_pct: topMatch ? parseFloat(topMatch[1]) : null,
          z_index: zMatch ? parseInt(zMatch[1]) : null,
        };
        
        players.push(player);
      });

      return { meta, team_colors: teamColors, players };
    });

    return squadData;
  } catch (e) {
    console.error('❌ 스쿼드 파싱 오류:', e.message);
    return null;
  }
}

// ============================================================================
// 게시글 상세 파서
// ============================================================================

async function parseArticleDetail(page, articleNo) {
  try {
    // 본문 내용
    const content = await page.evaluate(() => {
      const contentBody = document.querySelector('.content_body');
      if (!contentBody) return '';
      
      // img 태그를 [img 자리]로 대체
      const clone = contentBody.cloneNode(true);
      clone.querySelectorAll('img').forEach(img => {
        const placeholder = document.createTextNode('[img 자리]');
        img.parentNode.replaceChild(placeholder, img);
      });
      
      return clone.innerHTML.trim();
    });

    // 작성자 정보 (상세 페이지)
    const writerInfo = await page.evaluate(() => {
      const info = {};
      
      // 작성자 이름
      const nameEl = document.querySelector('.view_header .th.writer .name');
      info.name = nameEl?.textContent.trim() || '';
      
      // 레벨
      const lvEl = document.querySelector('.view_header .th.writer .lv .txt');
      info.level = parseInt(lvEl?.textContent.trim()) || 0;
      
      // 랭크 이미지
      const rankImg = document.querySelector('.view_header .th.writer .icon_rank img');
      info.rank_img = rankImg?.src || '';
      
      return info;
    });

    // 조회수, 추천, 비추천
    const stats = await page.evaluate(() => {
      const viewsEl = document.querySelector('.th.count');
      const likesEl = document.querySelector('.th.like');
      const dislikesEl = document.querySelector('.th.dislike');
      
      const viewsMatch = viewsEl?.textContent.match(/(\d+)/);
      const likesMatch = likesEl?.textContent.match(/(\d+)/);
      const dislikesMatch = dislikesEl?.textContent.match(/(\d+)/);
      
      return {
        views: viewsMatch ? parseInt(viewsMatch[1]) : 0,
        likes: likesMatch ? parseInt(likesMatch[1]) : 0,
        dislikes: dislikesMatch ? parseInt(dislikesMatch[1]) : 0,
      };
    });

    // 스쿼드 파싱
    const squad = await parseSquad(page);

    return {
      content,
      writer: writerInfo,
      ...stats,
      squad,
    };
  } catch (e) {
    console.error(`❌ 게시글 ${articleNo} 상세 파싱 오류:`, e.message);
    return null;
  }
}

// ============================================================================
// 메인 크롤러
// ============================================================================

async function crawl() {
  // 데이터 디렉토리 생성
  const dataDir = getTodayDataDir();
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
    console.log(`📁 데이터 폴더 생성: ${dataDir}`);
  }

  // 방문 기록 및 JSONL writer 초기화
  // visited.json은 data/ 폴더에 공용으로 저장 (날짜에 관계없이 중복 검사)
  const visitedManager = new VisitedManager();
  const jsonlWriter = new JsonlWriter(dataDir);

  // 1달 전 날짜 계산
  const cutoffDate = getDateMonthsAgo(CONFIG.MONTHS_TO_CRAWL);
  console.log(`📅 수집 기간: 오늘 ~ ${formatDateToYYMMDD(cutoffDate)}`);

  // GitHub Actions 환경 감지
  const isGitHubActions = process.env.GITHUB_ACTIONS === 'true';
  
  // 헤드리스 모드 설정 (GitHub Actions에서는 항상 headless)
  const headless = isGitHubActions || !process.argv.includes('--no-headless');
  console.log(`🌐 브라우저 모드: ${headless ? 'headless' : 'GUI'}${isGitHubActions ? ' (GitHub Actions)' : ''}`);

  // Puppeteer 브라우저 시작
  const browserArgs = [
    '--no-sandbox', 
    '--disable-setuid-sandbox',
    '--disable-blink-features=AutomationControlled',
  ];
  
  // GitHub Actions 환경에서 추가 args
  if (isGitHubActions) {
    browserArgs.push(
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--window-size=1920x1080'
    );
  }
  
  const browser = await puppeteer.launch({
    headless: headless ? 'new' : false,
    args: browserArgs,
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  
  // User-Agent 설정 (더 최신 버전으로)
  await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
  
  // webdriver 속성 숨기기 (봇 감지 우회)
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined,
    });
  });

  let pageNum = 1;
  let totalCrawled = 0;
  let shouldStop = false;
  let maxArticleNo = null;  // 크롤링 시작 시점의 최신 article_no (이 번호 이하만 수집)

  // Graceful shutdown 핸들러
  process.on('SIGINT', async () => {
    console.log('\n\n⚠️ 중단 요청 감지. 현재 상태 저장 중...');
    visitedManager.save();
    await browser.close();
    console.log(`✅ 저장 완료. 총 ${totalCrawled}개 게시글 수집됨.`);
    process.exit(0);
  });

  try {
    console.log(`\n🚀 크롤링 시작: ${CONFIG.BASE_URL}\n`);
    
    // 첫 페이지 로드
    await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle0', timeout: 60000 });
    console.log('📄 페이지 기본 로드 완료. 게시글 목록 대기 중...');
    
    // 충분한 대기 시간 (AJAX 로드 완료 대기)
    await sleep(5000);
    
    // 게시글 목록이 로드될 때까지 대기 - 여러 셀렉터 시도
    const selectors = [
      '.tbody .tr[data-no]',
      'div.tbody div.tr[data-no]',
      'div.tr[data-no]',
      '.list_wrap .tbody .tr',
    ];
    
    let foundSelector = null;
    for (const selector of selectors) {
      try {
        await page.waitForSelector(selector, { timeout: 5000 });
        foundSelector = selector;
        console.log(`✅ 게시글 목록 발견: ${selector}`);
        break;
      } catch (e) {
        console.log(`⏭️ 셀렉터 실패: ${selector}`);
      }
    }
    
    if (!foundSelector) {
      // 페이지 내용 직접 확인
      const pageContent = await page.content();
      console.log('⚠️ 게시글 셀렉터를 찾지 못함. 페이지 내용 분석 중...');
      
      // data-no 속성이 있는 요소 찾기
      const hasDataNo = pageContent.includes('data-no=');
      if (hasDataNo) {
        console.log('✅ data-no 속성 발견됨. 직접 파싱 시도...');
        foundSelector = '[data-no]';
      } else {
        console.log('❌ 게시글을 찾을 수 없습니다.');
        console.log('페이지 URL:', await page.url());
        throw new Error('게시글 목록을 찾을 수 없습니다');
      }
    }
    
    await sleep(1000);

    while (!shouldStop) {
      console.log(`\n📄 페이지 ${pageNum} 처리 중...`);
      
      // 게시글 목록이 로드될 때까지 대기
      await sleep(2000);
      
      // 디버깅: 페이지 구조 확인
      const debugInfo = await page.evaluate(() => {
        const tbody = document.querySelector('.tbody');
        const trs = document.querySelectorAll('.tbody .tr');
        const trsWithDataNo = document.querySelectorAll('.tbody .tr[data-no]');
        const allDataNo = document.querySelectorAll('[data-no]');
        
        // 첫 번째 tr의 HTML 확인
        const firstTr = trs[0];
        const firstTrHtml = firstTr ? firstTr.outerHTML.slice(0, 500) : 'no tr found';
        
        return {
          tbodyExists: !!tbody,
          trCount: trs.length,
          trWithDataNoCount: trsWithDataNo.length,
          allDataNoCount: allDataNo.length,
          firstTrHtml,
          firstDataNoValue: allDataNo[0]?.getAttribute('data-no') || 'none',
        };
      });
      
      console.log('🔍 디버그 정보:', JSON.stringify(debugInfo, null, 2));
      
      // 게시글 목록 가져오기
      const articles = await page.evaluate(() => {
        // .tbody .tr 에서 게시글 목록 가져오기
        const rows = document.querySelectorAll('.tbody .tr');
        
        return Array.from(rows).map(row => {
          // 게시글 번호는 href의 n4ArticleSN 파라미터에서 추출
          const titleEl = row.querySelector('.td.subject a');
          const href = titleEl?.getAttribute('href') || '';
          const articleNoMatch = href.match(/n4ArticleSN=(\d+)/);
          const articleNo = articleNoMatch ? parseInt(articleNoMatch[1]) : 0;
          
          // articleNo가 유효하지 않으면 스킵
          if (articleNo === 0) return null;
          
          const category = row.querySelector('.td.sort')?.textContent.trim() || '';
          const title = titleEl?.textContent.trim().replace(/\s+/g, ' ') || '';
          
          // 날짜 (.td.date의 data-no 속성에 전체 날짜가 있음)
          const dateEl = row.querySelector('.td.date');
          const datetimeRaw = dateEl?.getAttribute('data-no') || '';
          
          // 작성자
          const writerEl = row.querySelector('.td.writer .name');
          const writerName = writerEl?.textContent.trim() || '';
          const lvEl = row.querySelector('.td.writer .lv .txt');
          const writerLevel = parseInt(lvEl?.textContent.trim()) || 0;
          const rankImg = row.querySelector('.td.writer .icon_rank img')?.src || '';
          
          // 추천, 조회수
          const likes = parseInt(row.querySelector('.td.like')?.textContent.trim()) || 0;
          const views = parseInt(row.querySelector('.td.count')?.textContent.trim()) || 0;
          
          return {
            articleNo,
            category,
            title,
            href,
            datetimeRaw,
            writer: { name: writerName, level: writerLevel, rank_img: rankImg },
            likes,
            views,
          };
        }).filter(item => item !== null);  // null 항목 제거
      });

      // 유효한 게시글만 필터링
      const validArticles = articles.filter(a => a && a.articleNo > 0);
      console.log(`📋 발견된 게시글: ${validArticles.length}개`);

      if (validArticles.length === 0) {
        console.log('⚠️ 게시글이 없습니다. 크롤링 종료.');
        break;
      }

      // 첫 페이지에서 최신 article_no 기록 (크롤링 시작 시점 기준)
      if (pageNum === 1 && maxArticleNo === null) {
        maxArticleNo = Math.max(...validArticles.map(a => a.articleNo));
        console.log(`🔒 크롤링 기준점 설정: article_no <= ${maxArticleNo} (이 시점 이후 새 글은 무시)`);
      }

      // 각 게시글 처리
      let visitedDetailPage = false;  // 상세 페이지 방문 여부 추적
      let crawledInThisPage = 0;  // 이 페이지에서 수집한 게시글 수
      
      for (const article of validArticles) {
        // 크롤링 시작 이후에 올라온 새 글이면 스킵 (article_no가 더 큼)
        if (maxArticleNo !== null && article.articleNo > maxArticleNo) {
          console.log(`⏭️ [${article.articleNo}] 크롤링 시작 이후 새 글, 스킵`);
          continue;
        }
        // datetimeRaw가 없으면 스킵
        if (!article.datetimeRaw) {
          console.log(`⏭️ [${article.articleNo}] 날짜 정보 없음, 스킵`);
          continue;
        }
        
        // 날짜 체크 - 1달 전보다 오래된 게시글이면 종료
        try {
          const articleDate = parseDateFromDataNo(article.datetimeRaw);
          if (articleDate < cutoffDate) {
            console.log(`\n📅 1달 전 게시글 도달. 크롤링 종료.`);
            shouldStop = true;
            break;
          }
        } catch (dateErr) {
          console.log(`⚠️ [${article.articleNo}] 날짜 파싱 오류: ${article.datetimeRaw}`);
        }

        // 이미 방문한 게시글이면 스킵
        if (visitedManager.has(article.articleNo)) {
          console.log(`⏭️ [${article.articleNo}] 이미 수집됨, 스킵`);
          continue;
        }

        console.log(`\n📰 [${article.articleNo}] "${article.title.slice(0, 30)}..." 수집 중...`);

        try {
          // 게시글 상세 페이지로 이동 (3분 타임아웃)
          const articleUrl = `https://fconline.nexon.com${article.href}`;
          try {
            await page.goto(articleUrl, { waitUntil: 'networkidle2', timeout: CONFIG.TIMEOUT.PAGE_LOAD });
            visitedDetailPage = true;  // 상세 페이지 방문 표시
          } catch (timeoutErr) {
            if (timeoutErr.message.includes('timeout') || timeoutErr.message.includes('Timeout')) {
              console.log(`\n⏰ [${article.articleNo}] 페이지 로딩 타임아웃 (3분). 메인 목록으로 복귀 후 15분 대기...`);
              
              // 메인 목록으로 돌아가기
              try {
                await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle2', timeout: 60000 });
              } catch (e) {
                console.log('⚠️ 메인 목록 이동 실패, 브라우저 새로고침...');
                await page.reload({ waitUntil: 'networkidle2', timeout: 60000 });
              }
              
              // 15분 대기
              console.log(`⏸️ 15분 대기 중... (${new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })})`);
              await sleep(CONFIG.TIMEOUT.RECOVERY_WAIT);
              console.log(`✅ 대기 완료. 크롤링 재개... (${new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })})`);
              
              // 현재 페이지로 다시 이동
              await page.evaluate((pNum) => {
                if (typeof Article !== 'undefined' && Article.ArticleList) {
                  Article.ArticleList(null, pNum, '#divListPart', '', 'title', '1', '0', '/community/free/');
                }
              }, pageNum);
              await sleep(5000);
              
              // 이 게시글은 스킵하고 다음으로
              continue;
            }
            throw timeoutErr;
          }
          
          // 상세 정보 파싱
          const detail = await parseArticleDetail(page, article.articleNo);
          
          if (detail) {
            // 날짜 변환
            const articleDate = parseDateFromDataNo(article.datetimeRaw);
            const dateFormatted = formatDateToYYMMDD(articleDate);
            const dayOfWeek = getDayOfWeek(articleDate);
            
            // 데이터 구성
            const postData = {
              article_no: article.articleNo,
              category: article.category,
              title: article.title,
              writer: detail.writer || article.writer,
              likes: detail.likes,
              dislikes: detail.dislikes,
              views: detail.views,
              date: dateFormatted,
              day_of_week: dayOfWeek,
              datetime_raw: article.datetimeRaw,
              content: detail.content,
              squad: detail.squad,
              crawled_at: new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Seoul' }).replace(' ', 'T') + '+09:00',
            };

            // JSONL에 append
            jsonlWriter.append(postData);
            
            // 방문 기록 추가
            visitedManager.add(article.articleNo);
            
            totalCrawled++;
            crawledInThisPage++;  // 이 페이지에서 수집 카운트
            console.log(`✅ [${article.articleNo}] 저장 완료 (총 ${totalCrawled}개)`);
          }
        } catch (e) {
          console.error(`❌ [${article.articleNo}] 오류:`, e.message);
          visitedDetailPage = true;  // 오류 발생해도 상세 페이지 방문 시도함
        }

        // 게시글 간 딜레이
        const postDelay = randomDelay(CONFIG.DELAY.BETWEEN_POSTS_MIN, CONFIG.DELAY.BETWEEN_POSTS_MAX);
        await sleep(postDelay);
        
        // 10개 게시글마다 추가 휴식
        if (totalCrawled > 0 && totalCrawled % 10 === 0) {
          const postRestDelay = randomDelay(CONFIG.DELAY.EVERY_10_POSTS_MIN, CONFIG.DELAY.EVERY_10_POSTS_MAX);
          console.log(`⏸️ ${totalCrawled}개 수집 완료. ${Math.round(postRestDelay / 1000)}초 휴식...`);
          await sleep(postRestDelay);
        }
      }

      if (shouldStop) break;

      // 다음 페이지로 이동
      pageNum++;
      
      // 이 페이지에서 수집한 게시글이 있을 때만 휴식
      if (crawledInThisPage > 0) {
        // 10페이지마다 긴 휴식 (8~12분)
        if ((pageNum - 1) % 10 === 0) {
          const longDelay = randomDelay(CONFIG.DELAY.EVERY_10_PAGES_MIN, CONFIG.DELAY.EVERY_10_PAGES_MAX);
          console.log(`\n☕ ${pageNum - 1}페이지 완료 (${crawledInThisPage}개 수집). ${Math.round(longDelay / 60000)}분 휴식...`);
          await sleep(longDelay);
        }
        // 3페이지마다 휴식 (1~3분)
        else if ((pageNum - 1) % 3 === 0) {
          const shortDelay = randomDelay(CONFIG.DELAY.EVERY_3_PAGES_MIN, CONFIG.DELAY.EVERY_3_PAGES_MAX);
          console.log(`\n⏸️ ${pageNum - 1}페이지 완료 (${crawledInThisPage}개 수집). ${Math.round(shortDelay / 60000)}분 휴식...`);
          await sleep(shortDelay);
        }
      } else {
        console.log(`📄 페이지 ${pageNum - 1}: 새로 수집한 게시글 없음, 휴식 없이 계속 진행`);
      }

      // 상세 페이지를 방문했으면 목록 페이지로 돌아가기
      if (visitedDetailPage) {
        try {
          await page.goBack({ waitUntil: 'networkidle2', timeout: 15000 });
          await sleep(randomDelay(1500, 2500));
        } catch (goBackErr) {
          console.log('⚠️ goBack 실패, 목록 페이지로 직접 이동...');
          await page.goto(CONFIG.BASE_URL, { waitUntil: 'networkidle2', timeout: 30000 });
          await sleep(randomDelay(2000, 3000));
        }
      }
      // 방문하지 않았으면 이미 목록 페이지에 있음

      // 다음 페이지로 이동 (Article.ArticleList 함수 사용 - 가장 확실한 방법)
      try {
        console.log(`🔄 페이지 ${pageNum}로 이동 중...`);
        
        // Article.ArticleList 함수로 직접 페이지 이동
        const navigated = await page.evaluate((targetPage) => {
          if (typeof Article !== 'undefined' && Article.ArticleList) {
            Article.ArticleList(null, targetPage, '#divListPart', '', 'title', '1', '0', '/community/free/');
            return true;
          }
          return false;
        }, pageNum);
        
        if (!navigated) {
          // Article.ArticleList가 없으면 페이지네이션 버튼 클릭 시도
          const clicked = await page.evaluate((targetPage) => {
            const paginationItems = document.querySelectorAll('.pagination_wrap li');
            
            // 목표 페이지 번호 버튼 찾기
            for (const li of paginationItems) {
              const span = li.querySelector('span');
              if (span && span.textContent.trim() === String(targetPage)) {
                span.click();
                return { type: 'page', page: targetPage };
              }
            }
            
            // 목표 페이지가 없으면 "다음" 버튼 클릭
            const nextBtn = document.querySelector('.pagination_wrap .btn_next');
            if (nextBtn && !nextBtn.classList.contains('disabled')) {
              nextBtn.click();
              return { type: 'next' };
            }
            
            return null;
          }, pageNum);
          
          if (!clicked) {
            console.log('⚠️ 더 이상 페이지가 없습니다. 크롤링 종료.');
            break;
          }
          
          // "다음" 버튼을 눌렀으면 목표 페이지 버튼 다시 클릭
          if (clicked.type === 'next') {
            await sleep(randomDelay(2000, 3000));
            await page.evaluate((targetPage) => {
              const paginationItems = document.querySelectorAll('.pagination_wrap li');
              for (const li of paginationItems) {
                const span = li.querySelector('span');
                if (span && span.textContent.trim() === String(targetPage)) {
                  span.click();
                  return true;
                }
              }
              return false;
            }, pageNum);
          }
        }
        
        // AJAX 응답 대기 (타임아웃 3분, 실패 시 15분 대기 후 1회 재시도)
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
            console.log('⚠️ 메인 페이지 이동 실패, 페이지 새로고침 시도...');
            await page.reload({ waitUntil: 'networkidle2', timeout: 60000 });
          }
          
          // 15분 대기
          console.log(`🔄 메인 페이지로 이동 완료. ${Math.round(CONFIG.TIMEOUT.RECOVERY_WAIT / 60000)}분 대기 중...`);
          await sleep(CONFIG.TIMEOUT.RECOVERY_WAIT);
          console.log(`🔄 대기 완료, 페이지 ${pageNum}로 재이동 시도...`);
          
          // 다시 페이지 이동 시도
          await page.evaluate((targetPage) => {
            if (typeof Article !== 'undefined' && Article.ArticleList) {
              Article.ArticleList(null, targetPage, '#divListPart', '', 'title', '1', '0', '/community/free/');
            }
          }, pageNum);
          
          // 두 번째 시도
          pageLoaded = await waitForPageLoad(pageNum);
          
          if (!pageLoaded) {
            // 재시도도 실패 → 에러 throw (finally에서 아티팩트 저장됨)
            throw new Error(`❌ 페이지 ${pageNum} 이동 최종 실패 (재시도 후에도 응답 없음). 크롤링 중단.`);
          }
        }
        
        console.log(`📄 페이지 ${pageNum}로 이동 완료`);
        
      } catch (e) {
        console.log('⚠️ 페이지 이동 실패:', e.message);
        break;
      }

      // 페이지 간 딜레이
      const pageDelay = randomDelay(CONFIG.DELAY.BETWEEN_PAGES_MIN, CONFIG.DELAY.BETWEEN_PAGES_MAX);
      await sleep(pageDelay);
    }

  } catch (e) {
    console.error('❌ 크롤링 중 오류 발생:', e);
  } finally {
    await browser.close();
    console.log(`\n🎉 크롤링 완료! 총 ${totalCrawled}개 게시글 수집됨.`);
    console.log(`📁 저장 위치: ${dataDir}`);
    
    // JSONL 파일을 article_no 내림차순으로 재정렬
    const jsonlPath = path.join(dataDir, 'posts.jsonl');
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

// 실행
crawl().catch(console.error);
