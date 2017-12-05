#--------------------------------------------#
Sign.Dir       <- commandArgs(TRUE)[1]
In.RData.File  <- commandArgs(TRUE)[2]
Out.RData.File <- commandArgs(TRUE)[3]

#--------------------------------------------#
#Sign.Dir <- "."
#In.RData.File <- "signmatrix.RData"
#Out.RData.File <- "newsignmatrix.RData"

#--------------------------------------------#
Sign.Files    <- sprintf("%s/%s",Sign.Dir,list.files(pattern="TSS",path=Sign.Dir))
Sign.Files    <- Sign.Files[grep("TSS[0-9]+.sign$",Sign.Files)]
#--------------------------------------------#

#--------------------------------------------#
if (file.exists(In.RData.File) == TRUE) {
    #Sign.Files <- Sign.Files[which(file.info(Sign.Files)$mtime > file.info(In.RData.File)$mtime)]
   load(In.RData.File)
} else {
   Sign.Files <- Sign.Files
}
if (exists("signmatrix") == FALSE) { signmatrix <- matrix(ncol=0,nrow=0) }
#--------------------------------------------#

#--------------------------------------------#
Sign.Names <- gsub("\\.sign$","",basename(Sign.Files))
#Sign.Names <- gsub("\\.txt$","",basename(Sign.Files))
#--------------------------------------------#

#--------------------------------------------#
HGIDs <- c()
for (Sign.File in Sign.Files) {
   HGIDs <- unique(c(HGIDs,as.character(read.table(Sign.File,sep="\t",blank.lines.skip=TRUE,fill=TRUE,header=FALSE)[,3])))
}
HGIDs <- HGIDs[which(is.na(HGIDs)==FALSE)]
#--------------------------------------------#

#--------------------------------------------#
signmatrix <- signmatrix[setdiff(rownames(signmatrix),Sign.Names),]
#--------------------------------------------#

#--------------------------------------------#
m <- matrix(NA,ncol=ncol(signmatrix),nrow=length(Sign.Files),dimnames=list(Sign.Names,colnames(signmatrix)))
new.signmatrix <- rbind(signmatrix,m)
m <- matrix(NA,nrow=nrow(new.signmatrix),ncol=length(setdiff(HGIDs,colnames(signmatrix))),dimnames=list(rownames(new.signmatrix),setdiff(HGIDs,colnames(new.signmatrix))))
new.signmatrix <- cbind(new.signmatrix,m)
#--------------------------------------------#

#--------------------------------------------#
for (Sign.File in Sign.Files) {
   Sign.Name <- gsub("\\.sign$","",basename(Sign.File))
   #Sign.Name <- gsub("\\.txt$","",basename(Sign.File))
   #cat(Sign.File,"is loading...\n")
   Sign.Data <- read.table(Sign.File,sep="\t",blank.lines.skip=TRUE,fill=TRUE,header=FALSE)
   All.HGIDs <- unique(as.character(Sign.Data[which(is.na(Sign.Data[,3])== FALSE & Sign.Data[,5] == "0"),3]))
   new.signmatrix[Sign.Name,All.HGIDs] <- 0

   Up.HGIDs  <- unique(as.character(Sign.Data[which(is.na(Sign.Data[,3])== FALSE & Sign.Data[,5] == "1"),3]))
   Dw.HGIDs  <- unique(as.character(Sign.Data[which(is.na(Sign.Data[,3])== FALSE & Sign.Data[,5] == "-1"),3]))
   new.signmatrix[Sign.Name,setdiff(Up.HGIDs,Dw.HGIDs)] <- 1
   new.signmatrix[Sign.Name,setdiff(Dw.HGIDs,Up.HGIDs)] <- -1
}
#--------------------------------------------#

#--------------------------------------------#
signmatrix <- new.signmatrix
save(signmatrix,file=Out.RData.File)
#--------------------------------------------#

quit()
