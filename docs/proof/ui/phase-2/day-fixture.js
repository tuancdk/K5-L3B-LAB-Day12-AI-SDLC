// Phản hồi thử cho trình duyệt. Không được import vào game hoặc headless.
(() => {
  const forward = globalThis.fetch.bind(globalThis);
  const menu = {
    ca_loc_nuong_trui: { recipe:{ca_loc:1}, cook_s:6 },
    goi_bong_sung: { recipe:{bong_sung:2}, cook_s:4 }
  };
  const shop = { upgrades:{
    oxygen:[{level:1,price:200,oxygen_max_s:45},{level:2,price:400,oxygen_max_s:60}],
    hp:[{level:1,price:250,hp_max:4},{level:2,price:500,hp_max:5}]
  } };
  let state;
  const posts = [];
  let challengePause = false;
  function start() {
    state = {
      mode:"day", phase:"gather", state:"playing", tick:0, sim_tick:0, phase_tick:0, day:1,
      time_left_ticks:10800, reputation:3, money:200, earned:200, score:500, events:[],
      day_plan:{day:1, dishes:{ca_loc_nuong_trui:1,goi_bong_sung:1},ingredients:{ca_loc:1,bong_sung:2}},
      upgrades:{oxygen:0,hp:0}, active_upgrades:{oxygen:0,hp:0}
    };
    enter("gather");
    challengePause = false;
  }
  function event(name,data) {
    state.events.push({type:"event",tick:state.tick,phase:state.phase,day:state.day,name,data});
  }
  function enter(phase) {
    state.phase = phase;
    state.phase_tick = 0;
    state.time_left_ticks = phase === "shop" ? 600 : 10800;
    state.meta = {tick_hz:60,menu,shop};
    if (phase === "gather") {
      Object.assign(state,{
        player:{pos:[37,12],vel:[0,0],hp:3,hp_max:3,oxygen_ticks:0,oxygen_max_ticks:1800,catch_cd_ticks:18},
        hold:["ca_loc","bong_sung"],hold_count:2,hold_capacity:12,
        monsters:[{kind:"ca_sau",state:"chase",pos:[45,15]},{kind:"ca_sau",state:"recoil",pos:[86,20]}],
        nodes:[{id:"N5",kind:"keo_neo",pos:[76,0],ready:true},{id:"N6",kind:"keo_neo",pos:[90,0],ready:false,regrow_ticks:240}],
        fish:[{id:"F7",kind:"ca_keo",pos:[62,25],age_ticks:90}]
      });
      Object.assign(state.meta,{bounds:{x:[0,100],d:[0,30]},surface_depth:.5,dock_pos:[2,0],dock_radius:3,
        catch_radius:2,interact_radius:2,monsters:{species:{ca_sau:{detect_radius:10}}}});
    } else if (phase === "quan") {
      Object.assign(state,{stock:{ca_loc:1,bong_sung:2},player:{pos:[4,6],vel:[0,0]},shift_earned:0,hand:null,
        tables:[[9,2],[13,2],[9,6],[13,6]].map((pos,i)=>({pos,id:"T"+(i+1)})),
        stoves:[{id:"B1",pos:[2,8],state:"cooking",dish:{dish_id:"ca_loc_nuong_trui"},cook_ticks_left:180},
          {id:"B2",pos:[5,8],state:"ready",dish:{dish_id:"goi_bong_sung"}}],
        customers:[{id:"C1",table_id:"T1",dish_id:"ca_loc_nuong_trui",patience_ticks_left:900,state:"waiting"},
          {id:"C2",table_id:"T4",dish_id:"goi_bong_sung",patience_ticks_left:600,state:"waiting"}]});
      Object.assign(state.meta,{bounds:{x:[0,16],z:[0,10]},interact_radius:1.5,patience_s:60,reputation_max:5});
    }
  }
  function closeEvening() {
    event("served",{order_id:"C1",table_id:"T1",dish_id:"ca_loc_nuong_trui"});
    event("paid",{order_id:"C1",table_id:"T1",amount:72,tip:12});
    event("customer_left",{order_id:"C2",table_id:"T4"});
    state.reputation = 3.2;
    state.earned = 272;
    state.score = 572;
    event("quan_end",{shift_earned:72,reputation:3.2});
    enter("shop");
  }
  start();
  globalThis.dayTest = {enter,closeEvening,posts,get state(){return state;}};
  setInterval(() => {
    if (state.finished) return;
    state.tick++;
    if (state.state === "paused") return;
    state.sim_tick++;
    state.phase_tick++;
    state.time_left_ticks = Math.max(0,state.time_left_ticks-1);
  },1000/60);
  globalThis.fetch = async (url,opts) => {
    if (url === "/state") return new Response(JSON.stringify(state));
    if (url === "/restart") { start(); return new Response("{}"); }
    if (url === "/input") {
      const input = JSON.parse(opts.body);
      posts.push(input);
      if (input.pause === true && !challengePause) state.state = state.state === "paused" ? "playing" : "paused";
      if (typeof input.pause === "boolean") challengePause = input.pause;
      if (state.phase !== "shop" || state.state === "paused") return new Response("{}");
      if (input.buy) {
        const item = shop.upgrades[input.buy]?.[state.upgrades[input.buy]];
        if (!item || state.money < item.price) event("buy_failed",{action:input.buy,reason:item ? "funds" : "max_level"});
        else {
          state.upgrades[input.buy]++;
          state.money -= item.price;
          event("bought",{upgrade:input.buy,level:item.level,price:item.price,money:state.money});
        }
      }
      if (input.shop_done) {
        if (state.day === 5) Object.assign(state,{finished:true,state:"finished",days_completed:5});
        else { state.day++; enter("gather"); }
      }
      return new Response("{}");
    }
    return forward(url,opts);
  };
})();
