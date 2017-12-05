#--------------------------------------------#
Sign.In.File  <- commandArgs(TRUE)[1]
RData.File    <- commandArgs(TRUE)[2]
#--------------------------------------------#
#Sign.In.File <- "./TSP883_TSS11029.txt"
#RData.File   <- "./signmatrix.RData"

#--------------------------------------------#
Out.File      <- sprintf("%s.dist",Sign.In.File)
#--------------------------------------------#

#--------------------------------------------#
Sign.In.Name <- gsub("\\.sign$","",basename(Sign.In.File))
#Sign.In.Name <- gsub("\\.txt$","",basename(Sign.In.File))
load(RData.File)
if (exists("signmatrix") == FALSE) {
   cat("signmatrix does not exist\n")
}
#--------------------------------------------#
cat(dim(signmatrix))
print(Sign.In.Name)
print(Sign.In.File)
#--------------------------------------------#
New.Data <- matrix(NA,ncol=11,nrow=nrow(signmatrix))
rownames(New.Data) <- rownames(signmatrix)
Sign.In.values <- signmatrix[Sign.In.Name,]
for (Sign.Name in rownames(signmatrix)) {
   Sign.values    <- signmatrix[Sign.Name,]
   indexes        <- which(is.na(Sign.In.values) == FALSE & is.na(Sign.values) == FALSE)
   Sign.values    <- Sign.values[indexes]
   Sign.In.values <- Sign.In.values[indexes]
   #--------------------------------------------#

   #--------------------------------------------#
   euc.dist <- sqrt(sum((Sign.In.values - Sign.values) ^ 2))
   cor.dist <- cor(Sign.In.values,Sign.values)
   #--------------------------------------------#
   
   #--------------------------------------------#
   N <- length(Sign.values)
   R <- length(which(Sign.In.values != 0))
   n <- length(which(Sign.values != 0))
   r.IDs <- colnames(signmatrix)[indexes[which(Sign.values == Sign.In.values & Sign.values != 0)]]
   r <- length(r.IDs)
   rR <- r/(R+n-r)
   #--------------------------------------------#

   p.dist <- phyper(r-1,n,N-n,R,lower.tail=FALSE)
   z.dist <- (r-n*R/N) / sqrt( (n*R/N) * (1-R/N) * (1-(n-1)/(N-1)))

   #--------------------------------------------#
   New.Data[Sign.Name,1]  <- Sign.Name
   New.Data[Sign.Name,2]  <- r
   New.Data[Sign.Name,3]  <- R
   New.Data[Sign.Name,4]  <- n
   New.Data[Sign.Name,5]  <- N
   New.Data[Sign.Name,6]  <- rR
   New.Data[Sign.Name,7]  <- z.dist
   New.Data[Sign.Name,8]  <- p.dist
   New.Data[Sign.Name,9]  <- euc.dist
   New.Data[Sign.Name,10] <- cor.dist
   New.Data[Sign.Name,11] <- paste(r.IDs,collapse="|")
}
#--------------------------------------------#
New.Data <- New.Data[which(as.double(New.Data[,2]) > 0),,drop=FALSE]
New.Data <- New.Data[which(as.double(New.Data[,2]) != as.double(New.Data[,3]) & as.double(New.Data[,2]) != as.double(New.Data[,4])),,drop=FALSE]
#--------------------------------------------#

#--------------------------------------------#
New.Data <- New.Data[sort(as.double(New.Data[,7]),decreasing=TRUE,index.return=TRUE)$ix,]
#--------------------------------------------#

#--------------------------------------------#
write.table(gsub("^ +","",New.Data),file=Out.File,row.names=FALSE,col.names=FALSE,sep="\t",quote=FALSE)
#--------------------------------------------#

quit()

#--------------------------------------------#
New.Data2 <- New.Data
New.Data2[,1] <- Sign.In.File
New.Data2[,3] <- New.Data[,4]
New.Data2[,4] <- New.Data[,3]
for (i in 1:nrow(New.Data2)) {
    Sign.File <- New.Data[i,1]
    Out.File      <- sprintf("%s.signenr",Sign.File)
    cat(Sign.File,"\n")
        
    write.table(gsub("^ +","",New.Data2[i,,drop=FALSE]),file=Out.File,row.names=FALSE,col.names=FALSE,sep="\t",quote=FALSE,append=TRUE)
}
#--------------------------------------------#

quit()
