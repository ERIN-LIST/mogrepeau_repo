//###############################################################
//# mask1_slots.h for ProcessViewServer created: Tue Sep 1 15:03:06 2015
//# Yours: Lehrig Software Engineering
//###############################################################

// todo: uncomment me if you want to use this data aquisiton
// also uncomment this classes in main.cpp and pvapp.h
// also remember to uncomment rllib in the project file
//extern rlModbusClient     modbus;  //Change if applicable
//extern rlSiemensTCPClient siemensTCP;
//extern rlPPIClient        ppi;
extern rlOpcXmlDa opc;
#include <list>


typedef struct 
{
  rlSvgAnimator svgAniL;
  rlSvgAnimator svgAniM;
  rlSvgAnimator svgAniR;
  int EPA_zLife;
}
DATA;

int S0_SBit;
float yMax=771.391931;
float yRange=695.84015;
float bRange=5.0;

struct image 
{
  const char* name;
  int widget;
  int bitloc;
};

struct ampelBitsStruct
{
  int widget;
  int bits[2];
  const char* opcAutonomie;
  const char* opcLevel;
};

struct ampelBitcodeStruct
{
  const char* svgId;
  int code;
  int range[2];
};

image imageArray[10] = {
//This is where the images are related to the integer images from 1 to 10
//relate to binary values from top to bottom: 7 is all initialisation images, 
//56 is winter, 448 is summer and 518 is fire
  {"./images/01IndNormal.jpg", industrial, 1},
  {"./images/01RuralNormal.jpg", rural, 2},
  {"./images/01CityNormal.jpg", city, 3},
  {"./images/02IndWinter.jpg", industrial, 4},
  {"./images/02RuralWinter.jpg", rural, 5},
  {"./images/02CityWinter.jpg", city, 6},
  {"./images/03IndSummer.jpg", industrial, 7},
  {"./images/03RuralSummer.jpg", rural, 8},
  {"./images/03CitySummer.jpg", city, 9},
  {"./images/04IndFire.jpg", industrial, 10}
};

std::list<image> imageList(imageArray, imageArray + sizeof(imageArray)/ sizeof(imageArray[0]));

ampelBitsStruct ampelBits[3] = {
  {BasinSVGL, {11,12}, "GPC_S01_Autonomie","DB102 GPC_EPA_S01_H01"},
  {BasinSVGM, {13,14}, "GPC_S02_Autonomie","DB102 GPC_EPA_S02_H01"},
  {BasinSVGR, {15,16}, "GPC_S03_Autonomie","DB102 GPC_EPA_S03_H01"}
};

ampelBitcodeStruct ampelBitcode[3] = {
  {"legVert", 1, {20,28}},
  {"legOrange", 2, {2,48}},
  {"legRouge", 3, {0,100}}
};

static int drawSVG(PARAM *p, int id, rlSvgAnimator *svgAni)
//helpfunction to draw the SGV
{
  //if(d->svgAnimator.isModified == 0) return 0;
  gBeginDraw(p,id);
  svgAni->writeSocket();
  gEndDraw(p);
  return 0;
}

static int slotInit(PARAM *p, DATA *d)
//Initialisation
{
  if(p == NULL || d == NULL) return -1;
  const char *cptr;

  cptr = toolTip[S0_ScenarioBit];

  //memset(d,0,sizeof(DATA));
  pvResize(p,0,1920,1080);

  // Initialise life counter
  d->EPA_zLife = 0;

//Initialise the SGVs
  d->svgAniL.setSocket(&p->s);
  d->svgAniL.setId(BasinSVGL);
  d->svgAniL.read("basin_with.svg");
  pvSetBufferTransparency(p,BasinSVGL,0);
  drawSVG(p,BasinSVGL,&d->svgAniL);
  pvRequestGeometry(p,BasinSVGL);
  pvRequestParentWidgetId(p,BasinSVGL);

  d->svgAniM.setSocket(&p->s);
  d->svgAniM.setId(BasinSVGM);
  d->svgAniM.read("basin_with.svg");
  d->svgAniM.svgSearchAndReplace("WaterTowerBkg","xlink:href=","Wasserturm_industrie.png","Wasserturm_rural.png");
  pvSetBufferTransparency(p,BasinSVGM,0);
  drawSVG(p,BasinSVGM,&d->svgAniM);
  pvRequestGeometry(p,BasinSVGM);
  pvRequestParentWidgetId(p,BasinSVGM);

  d->svgAniR.setSocket(&p->s);
  d->svgAniR.setId(BasinSVGR);
  d->svgAniR.read("basin_with.svg");
  d->svgAniR.svgSearchAndReplace("WaterTowerBkg","xlink:href=","Wasserturm_industrie.png","Wasserturm_city.png");
  pvSetBufferTransparency(p,BasinSVGR,0);
  drawSVG(p,BasinSVGR,&d->svgAniR);
  pvRequestGeometry(p,BasinSVGR);
  pvRequestParentWidgetId(p,BasinSVGR);

  S0_SBit = opc.intValue(cptr);

  return 0;
}


static int slotNullEvent(PARAM *p, DATA *d)
{
  if(p == NULL || d == NULL) return -1;
  
  // only act if something needs to be done (EPA life counter has changed)
  if(trace) printf("EPA zLife (pvb,opc) %d, %f\n",d->EPA_zLife, opc.floatValue("EPA_zLive"));
  if(d->EPA_zLife == opc.intValue("EPA_zLive")) return 0;
  else{
    d->EPA_zLife = opc.intValue("EPA_zLive");
  }

  const char *cptr;
  int autonomie_i;
  double level_i,scalF,dy;
  rlSvgAnimator anim;

  cptr = toolTip[S0_ScenarioBit];
  S0_SBit = opc.intValue(cptr);
  pvPrintf(p,S0_ScenarioBit,"%s=%s",cptr,opc.stringValue(cptr));

  //Loop over the imagebits in S0_SBit to update the background images
  for (int i = 0; i < 10; i++) {
    if (((S0_SBit >> i) & 1) == 1) {
      pvSetImage(p, imageArray[i].widget, imageArray[i].name);
//  for (std::list<image>::iterator imageIt = imageList.begin(); imageIt != imageList.end(); ++imageIt) {
//    if (((S0_SBit >> imageIt->bitloc) & 1) == 1) {
//      pvSetImage(p, imageIt->widget, imageIt->name);
    }
  }

  //Handle the Autonomy information for the SVG ampel of the basins and
  // Level information of the basins
  scalF = yRange/bRange;
  int sizeAB = sizeof(ampelBits)/sizeof(ampelBitsStruct);
  int sizeABC = sizeof(ampelBitcode)/sizeof(ampelBitcodeStruct);
  for (int i = 0; i < sizeAB; i++){
    //get the opc values
    autonomie_i = opc.intValue(ampelBits[i].opcAutonomie);
    level_i = opc.floatValue(ampelBits[i].opcLevel);
    if(trace) printf("Basin %d: OPCVariables = %d, %f \n",i,autonomie_i,level_i);
    //get the animator corresponding to the widget
    if (i == 0){ anim = d->svgAniL; }
    else if (i == 1){ anim = d->svgAniM; }
    else if (i == 2){ anim = d->svgAniR; }
    //set the water rectangle in the svg.
    dy = level_i*scalF;
    anim.svgPrintf("rectWater", "height=","%f",dy);
    anim.svgPrintf("rectWater", "y=","%f",yMax-dy);
    bool set=false;
  for (int j = 0; j < sizeABC; j++){
    //GScToDo: this is not working to reset opacity for the higher lights
    if ((not set) && (autonomie_i >= ampelBitcode[j].range[0]) && (autonomie_i <= ampelBitcode[j].range[1])){
      anim.svgSearchAndReplace(ampelBitcode[j].svgId, "style=", "fill-opacity:","fill-opacity:1");
      set = true;
    }
    else{
      anim.svgSearchAndReplace(ampelBitcode[j].svgId, "style=", "fill-opacity:","fill-opacity:0.2");
    }
  }
    drawSVG(p,ampelBits[i].widget,&anim);
  }
  
  return 0;
}

static int slotButtonEvent(PARAM *p, int id, DATA *d)
{
  if(p == NULL || id == 0 || d == NULL) return -1;
  return 0;
}

static int slotButtonPressedEvent(PARAM *p, int id, DATA *d)
{
  if(p == NULL || id == 0 || d == NULL) return -1;
  return 0;
}

static int slotButtonReleasedEvent(PARAM *p, int id, DATA *d)
{
  if(p == NULL || id == 0 || d == NULL) return -1;
  return 0;
}

static int slotTextEvent(PARAM *p, int id, DATA *d, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || text == NULL) return -1;
  return 0;
}

static int slotSliderEvent(PARAM *p, int id, DATA *d, int val)
{
  if(p == NULL || id == 0 || d == NULL || val < -1000) return -1;
  return 0;
}

static int slotCheckboxEvent(PARAM *p, int id, DATA *d, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || text == NULL) return -1;
  return 0;
}

static int slotRadioButtonEvent(PARAM *p, int id, DATA *d, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || text == NULL) return -1;
  return 0;
}

static int slotGlInitializeEvent(PARAM *p, int id, DATA *d)
{
  if(p == NULL || id == 0 || d == NULL) return -1;
  return 0;
}

static int slotGlPaintEvent(PARAM *p, int id, DATA *d)
{
  if(p == NULL || id == 0 || d == NULL) return -1;
  return 0;
}

static int slotGlResizeEvent(PARAM *p, int id, DATA *d, int width, int height)
{
  if(p == NULL || id == 0 || d == NULL || width < 0 || height < 0) return -1;
  return 0;
}

static int slotGlIdleEvent(PARAM *p, int id, DATA *d)
{
  if(p == NULL || id == 0 || d == NULL) return -1;
  return 0;
}

static int slotTabEvent(PARAM *p, int id, DATA *d, int val)
{
  if(p == NULL || id == 0 || d == NULL || val < -1000) return -1;
  return 0;
}

static int slotTableTextEvent(PARAM *p, int id, DATA *d, int x, int y, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || x < -1000 || y < -1000 || text == NULL) return -1;
  return 0;
}

static int slotTableClickedEvent(PARAM *p, int id, DATA *d, int x, int y, int button)
{
  if(p == NULL || id == 0 || d == NULL || x < -1000 || y < -1000 || button < 0) return -1;
  return 0;
}

static int slotSelectionEvent(PARAM *p, int id, DATA *d, int val, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || val < -1000 || text == NULL) return -1;
  return 0;
}

static int slotClipboardEvent(PARAM *p, int id, DATA *d, int val)
{
  if(p == NULL || id == 0 || d == NULL || val < -1000) return -1;
  return 0;
}

static int slotRightMouseEvent(PARAM *p, int id, DATA *d, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || text == NULL) return -1;
  //pvPopupMenu(p,-1,"Menu1,Menu2,,Menu3");
  return 0;
}

static int slotKeyboardEvent(PARAM *p, int id, DATA *d, int val, int modifier)
{
  if(p == NULL || id == 0 || d == NULL || val < -1000 || modifier < -1000) return -1;
  return 0;
}

static int slotMouseMovedEvent(PARAM *p, int id, DATA *d, float x, float y)
{
  if(p == NULL || id == 0 || d == NULL || x < -1000 || y < -1000) return -1;
  return 0;
}

static int slotMousePressedEvent(PARAM *p, int id, DATA *d, float x, float y)
{
  if(p == NULL || id == 0 || d == NULL || x < -1000 || y < -1000) return -1;
  return 0;
}

static int slotMouseReleasedEvent(PARAM *p, int id, DATA *d, float x, float y)
{
  if(p == NULL || id == 0 || d == NULL || x < -1000 || y < -1000) return -1;
  return 0;
}

static int slotMouseOverEvent(PARAM *p, int id, DATA *d, int enter)
{
  if(p == NULL || id == 0 || d == NULL || enter < -1000) return -1;
  return 0;
}

static int slotUserEvent(PARAM *p, int id, DATA *d, const char *text)
{
  if(p == NULL || id == 0 || d == NULL || text == NULL) return -1;
  return 0;
}
