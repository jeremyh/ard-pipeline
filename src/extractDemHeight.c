/*****************************************************************
 * Extract the DEM value from a 1 deg square DEM based on lat/long
 *
 *    unsigned integer value
 *
 * @author: Paul Gardner  Created on: 04/06/2008
 *
 *    command line: extractDemHeight DEM_geoTiff_file Lat Long
 *
 *****************************************************************
 */

#include <time.h>
#include <stdio.h>
#include "extractDemHeight.h"

char DEM_file[200], LatString[20], LongString[20];
float Lat, Long;

int main (int argc, char** argv)
{
  verbose = TRUE;

  // Variables for the CPU time when running the program
  setCPUTimer ();    // set the first stage time
  startTimer = prevTimer;

  // Parse command line inputs including arguments and options
  // if (length(argv) != 3)
  // usage ();

  strcpy(DEM_file, argv[1]);
  strcpy(LatString, argv[2]);
  strcpy(LongString, argv[3]);

  sscanf(LatString, "%f", &Lat);
  sscanf(LongString, "%f", &Long);

  Gtif DEM_Gtif;

  // Initialize the Gtif file and set up parameters
  setupGtif (&DEM_Gtif, DEM_file);

  // certain valus are assumed...
  DEM_Gtif.UL[0] = 108.0;  // in decimal degs
  DEM_Gtif.UL[1] = -8.0;
  DEM_Gtif.UL[2] = 0.0;

  DEM_Gtif.LL[0] = 108.0;
  DEM_Gtif.LL[1] = -48.0;
  DEM_Gtif.LL[2] = 0.0;

  DEM_Gtif.UR[0] = 157.99999999;
  DEM_Gtif.UR[1] = -8.0;
  DEM_Gtif.UR[2] = 0.0;

  DEM_Gtif.LR[0] = 157.99999999;
  DEM_Gtif.LR[1] = -48.0;
  DEM_Gtif.LR[2] = 0.0;

  DEM_Gtif.scaleX = 1.0;
  DEM_Gtif.scaleY = 1.0;

  // Check Lat/Long not outside image:
  if ((Lat > DEM_Gtif.UL[1]) || (Lat < DEM_Gtif.LR[1])) {
    fprintf (stderr, "ERROR: Lat %f out of range\n", Lat);
    exit(1);
  }
  if ((Long < DEM_Gtif.UL[0]) || (Long > DEM_Gtif.LR[0])) {
    fprintf (stderr, "ERROR: Long %f out of range\n", Long);
    exit(1);
  }


  int LineNo = 20;
  int PixelNo = 20;

  // Calculate Line and Pixel Number:

  LineNo = (int)( -(Lat - DEM_Gtif.UL[1]));
  PixelNo = (int)(Long -  DEM_Gtif.LL[0]);

  if (LineNo < 0 || LineNo > DEM_Gtif.height) {
    fprintf (stderr, "ERROR: Calculated LineNo %d out of range (%d)\n", LineNo, DEM_Gtif.height);
    exit(1);
  }
  if (PixelNo < 0 || PixelNo > DEM_Gtif.width) {
    fprintf (stderr, "ERROR: Calculated PixelNo %d out of range (%d)\n", PixelNo, DEM_Gtif.width);
    exit(1);
  }

  // printf("Line: %d, Pixel: %d \n", LineNo, PixelNo);

  // count CPU time for the whole processing
  if (verbose)
      fprintf (stdout, "\n    Total CPU time for the whole composite processing: %s.\n",
	       toTimeString(difftime(time(NULL), startTimer)));

  uint16 ElevVal = readDEMvalue(&DEM_Gtif, LineNo, PixelNo);

  printf("Line: %d, Pixel: %d, DEM value: %u \n", LineNo, PixelNo, ElevVal);

  // Close all open GeoTIFF files before output JPEG image

  closeGtif(&DEM_Gtif);

  // fprintf (stdout,"ElevValue = %u \n" , ElevVal);

  // Set exit status to be 0 on successful execution
  exit (0);

}


uint16 readDEMvalue(Gtif *inGtif, int LineNo, int PixelNo)
// Extract DEM value by Line and Piixel
// Line/Pixel offset from (0,0)

{

    int fileNo, winLineNo, pixelNo, gtifY;   // , bytesRead
    uint16 *tmpBuf;
    uint16 ElevValue;

    tmpBuf = (uint16 *)malloc(inGtif->scanlineSize);

    if (TIFFReadScanline (inGtif->tif, tmpBuf, (uint32)LineNo, 0)<=0)
      {
	fprintf(stderr, "  Error: Failed in reading scanline %d\n", gtifY);
	exit(11);
      }

    // printf("For Line %d\n", LineNo);
    // printf("Col  %u %u, %u \n", tmpBuf[PixelNo-1], tmpBuf[PixelNo], tmpBuf[PixelNo+1]);

    ElevValue = tmpBuf[PixelNo];

    free (tmpBuf);

    return ElevValue;


}


// Return true if having successfully opened a GeoTIFF file and extract relavent metadata.
boolean setupGtif (Gtif *gtif, char *fileName)
{
	if (fileName == (char *)NULL)
		return FALSE;

	// Open the file, read the Gtif information, and print to stdout.
	gtif->tif = (TIFF*)NULL;  /* TIFF-level descriptor */
	gtif->tif = TIFFOpen(fileName, "r");
	if (!gtif->tif)
	{
		fprintf(stderr, "    Error: cannot open file \"%s\".\n", fileName);
		return FALSE;
	}

	TIFFGetField(gtif->tif, TIFFTAG_SAMPLESPERPIXEL, &(gtif->samplesPerPixel));
	if (!TIFFGetField(gtif->tif, TIFFTAG_BITSPERSAMPLE,&(gtif->bitsPerSample)))
    {
        fprintf (stderr, "---- Error: cannot extract bitsPerSample for %s.\n", fileName);
		return FALSE;
    }

    if (gtif->bitsPerSample > 8 && gtif->bitsPerSample <= 16)
        gtif->bitsPerSample = 16;

	// size of the GeoTIFF image
	TIFFGetField(gtif->tif, TIFFTAG_IMAGEWIDTH, &(gtif->width));
	TIFFGetField(gtif->tif, TIFFTAG_IMAGELENGTH, &(gtif->height));

	int count;

	gtif->scaleX = (double)gtif->width/jpgWidth;
	gtif->scaleY = (double)gtif->height/jpgHeight;

	if (!TIFFGetField (gtif->tif, GTIFF_PIXELSCALE, &count, &(gtif->pixelSize)))
	  {
	    fprintf(stderr, "    Error: cannot extract pixel size.\n");
	    exit(11);
	  }
     	// printf("Number of pixel scale points: %d\n", count);

	gtif->windowSize = (int)(gtif->scaleY+1);
	gtif->scanlineSize = gtif->width*(gtif->bitsPerSample/8);  // TIFFScanlineSize(gtif->tif);
	gtif->byteOrder = LITTLE_ENDIAN;
	gtif->lineNo = -1;   // No if the scanline read/buffered

	if (!TIFFGetField (gtif->tif, GTIFF_TIEPOINTS, &count, &(gtif->tiePoints)))
	  {
	    fprintf (stderr, "    Error: cannot extract tie points.\n");
	    exit(11);
	  }
	// printf("Number of Tie points: %d\n", count);

	// allocate memory to all scanline buffers
	int i;
	gtif->scanlines = (uint16 **)malloc(gtif->scanlineSize*gtif->windowSize);  // *sizeof(uint16 *)
	for (i = 0; i < gtif->windowSize; i ++)
	  {
	    gtif->scanlines[i] = (uint16 *)malloc(gtif->scanlineSize);  // *sizeof(uint16)
	    if (gtif->scanlines[i] == (uint16 *)NULL)
	      {
		fprintf (stderr, "    Error: cannot allocate memory to %d-th scanline.\n", (i+1));
		exit(13);
	      }
	  }

	if (gtif->bitsPerSample != 16)
	{
		fprintf(stderr, "  Error: Unsupported BitsPerSample %d\n", gtif->bitsPerSample);
		fprintf(stderr, "  This Program currently only support 16 bits (2 bytes) GeoTIFF. Exit!\n");
		exit(11);
	}

	if (verbose)
	{
		printf("Param=Values from %s\n", fileName);
		printf("samplesPerPixel=%d, bitsPerSample=%d\n", gtif->samplesPerPixel, gtif->bitsPerSample);
		printf("width=%d, height=%d, scanlineSize=%d\n", gtif->width, gtif->height, gtif->scanlineSize);
		//	printf("scaleX=%g, scaleY=%g, windowSize=%d\n", gtif->scaleX, gtif->scaleY, gtif->windowSize);
		// printf("\n");
	}

	// successfully extracted all metadata
	return TRUE;
}

// close the opened getiff file and release its memory
void closeGtif (Gtif *gtif)
{
	if (gtif == (Gtif *)NULL)
		return;

    int i;
	for (i = 0; i < gtif->windowSize; i ++)
    {
        if (gtif->scanlines[i] != (uint16 *)NULL)
            free (gtif->scanlines[i]);
    }

    free (gtif->scanlines);

	if (gtif->tif != (TIFF *)NULL)
		TIFFClose (gtif->tif);
}


const char *mainUsage = "Usage: extractDemHeight <GeoTIFF_DEM_File> <Lat> <Long>";

// print the usage information about the program and then exit
void usage()
{
	fprintf(stdout, "%s\n", mainUsage);
	fprintf(stdout, "Where:\n");
	fprintf(stdout, "      <GeoTIFF_DEM_File>:  \",\"\n");
	fprintf(stdout, "      <Lat> <Long>: Decimal coords of the required Elevation\n");
    exit(12);
}


// parse input folder string into folder names delimited by comma ','
void parseInputFileList (char *fileList)
{
	// parse input folder names from command line
	char *word = strtok (fileList, ", ");
	while (word != (char *)NULL)
	{
		if (inFileNames[numOfInFiles] == (char *)NULL)
			inFileNames[numOfInFiles] = (char *)malloc (strlen(word)+1);
		if (inFileNames[numOfInFiles] == (char *)NULL)
		{
			fprintf(stderr, "    Error: cannot allocate memory to \"inputFileNames\".\n");
			exit (10);
		}

		trim (word);
		if (word == (char *)NULL)
			continue;

		strcpy (inFileNames[numOfInFiles++], word);
		word = strtok (NULL, ",");
	}
}

// set the CPU timer
void setCPUTimer ()
{
    prevTimer = time(NULL); // start to count CPU time
}

// get the CPU time duration in a specific stage
long getStageTime ()
{
    time_t thisTimer = time(NULL);
    double duration = difftime (thisTimer, prevTimer);

    prevTimer = thisTimer;

    return (long)duration;
}

// Convert the time in milli-seconds into a formatted string
// of "hours:minutes:seconds.milli-seconds"
// e.g., "001:38:24.567" and "000:00:00.000"
char *toTimeString (long int duration)
{
    int hours = duration / 3600;

    // total seconds less than a hour
    long total_seconds = duration % 3600;

    int minutes = total_seconds/60;
    int seconds = total_seconds%60;

    char *timeString = (char *)malloc(10*sizeof(char));
    if (hours == 0)
    {
        if (minutes == 0 && seconds == 0)
                sprintf (timeString, "< %d second", 1);
        else
            sprintf (timeString, "%dm:%ds", minutes, seconds);
    }
    else
        sprintf (timeString, "%dh:%dm:%ds", hours, minutes, seconds);

    return timeString;
}

